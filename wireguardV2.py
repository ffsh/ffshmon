#!/usr/bin/env python3

import subprocess
import re
import sys
import os
import socket
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email import utils
import click



def collect(interface, attempt=0):
    """Helper Method, Call wg command to check for latest handshake"""
    result = subprocess.run(['wg', 'show', interface, 'latest-handshakes'], stdout=subprocess.PIPE) 
    match = re.search(r"(\d{10,})", result.stdout.decode('utf-8'))
    hand_shake = datetime.now() - datetime.fromtimestamp(int(match[1]))
    delta = hand_shake.total_seconds()
    if attempt == 0 and delta == 0:
        logging.info("Attempt {} failed, trying again".format(attempt))
        collect(attempt=1)
    return delta

def wg_status(interface):
    """Call collect and evaluate result"""
    try:
        delta = collect(interface=interface)
    except Exception as e:
        return 'failed'
    if delta == 0:
        handshake_status = 'failed'
    elif delta <= 120:
        handshake_status = 'ok'
    elif delta <= 135:
        handshake_status = 'ok' #pending
    elif delta <= 180:
        handshake_status = 'ok'#retry
    else:
        handshake_status = 'failed'
    return handshake_status

def test_interface(interface_name):

    # Run Request via interface 
    logging.info("Trying to reach google via VPN interface.")
    subprocess.run(['curl', '--connect-timeout', '10', '--interface', interface_name, 'https://www.google.com'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Check wireguard for status
    logging.info("Checking wireguard status")
    current_status = wg_status(interface_name)
    return current_status

def new_config(interface):
    subprocess.run(['python3', '/opt/wg-conf-gen/wg-conf-gen.py', 'recreate'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info("Recreated wireguard config")
    subprocess.run(['systemctl', 'restart', f'wg-quick@{interface}.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info("Restarted wireguard service")

def stop_fastd():
    subprocess.run(['systemctl', 'restart', 'fastd@ffsh.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info("Stopped fastd service")

def send_mail(config, message):
    """ send mail according to config"""
    msg = MIMEText(message)
    msg['Subject'] = "Wireguard is down on {}".format(socket.gethostname())
    msg['From'] = config["user"]
    msg['To'] = config["target"]
    msg['Date'] = utils.formatdate(localtime=True)

    try:
        server = smtplib.SMTP_SSL(host=config["host"], port=config["port"], timeout=10)
        # server.set_debuglevel(1)

        server.login(config["user"], config["password"])
        server.sendmail(config["user"], config["target"], msg.as_string())
    except socket.gaierror:
        logging.error("DNS resolution failed for {}".format(config["host"]))

def action(interface, mail_config):
    """Take action based on status"""
    status = test_interface(interface)
    if status == 'ok':
        logging.info("Everything ok, done.")
        sys.exit(0)
    else:
        logging.info("Status is failed, taking action")
        new_config(interface)
        # retest interface
        re_status = test_interface(interface)
        logging.info("Re-tested the interface after new config and restart")
        if re_status == 'failed':
            logging.info("No success, wg tunnel still down")

            logging.info("Stop fastd service")
            send_mail(mail_config, "Wireguard config was re-created but wireguard is still down!\nFastd service was stopped.")
            logging.info("Mail send")
            
# Cli group, could add more commands in the future
@click.group()
def cli():
    pass

@cli.command()
@click.option('--user', help='Mail address', required=True)
@click.option('--password', help='Password for Mail Address', required=True)
@click.option('--log', help='Path to log file', required=True)
def check(user, password, log):
    """Check Status of wireguard interface"""

    # Create log file if it does not exist
    try:
        with open(log, "x") as file:
            # This part will only execute if the file is created successfully
            pass
    except FileExistsError:
        pass


    config = {
    "target": "benjamin@freifunk-suedholstein.de",
    "host": "mail.freifunk-suedholstein.de",
    "port": "465",
    "user": user,
    "password": password
    }
    action("exit", config)
    # LogLevel DEBUG, INFO, WARNING, ERROR
    log_level = logging.INFO
    log_format = '%(asctime)s %(levelname)-8s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    logging.basicConfig(format=log_format, datefmt=date_format, filename=log, encoding='utf-8', level=log_level)


if __name__ == "__main__":
    cli()