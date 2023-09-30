#! python3

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

# LogLevel DEBUG, INFO, WARNING, ERROR
log_level = logging.WARNING

# path for logfile path has to exist and be writeable
log_file = "/var/log/ffshmon/ffshmon.log"

# Path for the marker
path_marker = "/tmp/ffshmon_marker"

def test_connection():
    subprocess.run(['curl', '--connect-timeout', '10', '--interface', 'exit', 'https://www.google.com'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def collect(attempt=0):
    result = subprocess.run(['wg', 'show', 'exit', 'latest-handshakes'], stdout=subprocess.PIPE) 
    match = re.search(r"(\d{10,})", result.stdout.decode('utf-8'))
    hand_shake = datetime.now() - datetime.fromtimestamp(int(match[1]))
    delta = hand_shake.total_seconds()
    if attempt == 0 and delta == 0:
        logging.info("Attempt {} failed, trying again".format(attempt))
        collect(attempt=1)
    return delta

def get_status():
    try:
        delta = collect()
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


def get_health():

    try:
        current_status = get_status()
    except Exception as e:
        return "Health status is not good, received error: {}".format(e)

    if current_status == "ok":
        return "Health status is ok."
    else:
        return "Health status is {}".format(current_status), 500

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


def create_file_maker(path):
    open(path, mode='a').close()

def remove_file_marker(path):
    if os.path.exists(path):
        os.remove(path)

def check_file_marker(path):
    # returns true if file exists and is not expired else returns false
    if not os.path.exists(path):
        logging.info("Marker file does not exist")
        return False
    else:
        logging.info("Marker file does exist checking timestamp")
        creation_time = datetime.fromtimestamp(os.path.getctime(path))
        logging.debug("creation_time: {}".format(creation_time))
        
        passed_time = creation_time - datetime.now()
        
        logging.debug("passed time {}".format(passed_time.total_seconds()))
        
        if abs(passed_time.total_seconds()) >= 14400:
            remove_file_marker(path)
            logging.info("Time has passed, removed file")
            return False
        else: 
            logging.info("Time has not passed, please wait")
            return True

if __name__ == "__main__":

    log_format = '%(asctime)s %(levelname)-8s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    try:
        logging.basicConfig(format=log_format, datefmt=date_format, filename=log_file, encoding='utf-8', level=log_level)
    except FileNotFoundError:
        logging.warning("Logfile not found, logging to stdout")
        logging.basicConfig(format=log_format, datefmt=date_format, level=log_level, force=True)

    try:
        config = {
            "target": "noc@freifunk-suedholstein.de",
            "host": "mail.freifunk-suedholstein.de",
            "port": "465",
            "user": sys.argv[1],
            "password": sys.argv[2]
        }
    except IndexError:
        logging.error("User and Password are required, python3 wireguard.py $user $password")
        exit()
    
    try:
        if sys.argv[3] == "test":
            logging.info("Sending test mail")
            send_mail(config, "test")    
    except IndexError:
        try:
            test_connection()
            status = get_health()
            if status != "Health status is ok.":
                if not check_file_marker(path_marker):
                    send_mail(config, "Host: {}\n{}".format(socket.gethostname(), status))
                    create_file_maker(path_marker)
                else:
                    logging.info("Not sending mail, marker exists and is valid.")
            else:
                logging.info("Status was ok, removing marker if it exists")
                remove_file_marker(path_marker)
        except TimeoutError:
            logging.error("Timeout, couldn't send mail.")