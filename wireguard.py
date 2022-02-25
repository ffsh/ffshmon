#! python3

import subprocess
import re
import sys
import socket
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email import utils

def collect(attempt=0):
    result = subprocess.run(['wg', 'show', 'exit', 'latest-handshakes'], stdout=subprocess.PIPE) 
    match = re.search(r"(\d{10,})", result.stdout.decode('utf-8'))
    hand_shake = datetime.now() - datetime.fromtimestamp(int(match[1]))
    delta = hand_shake.total_seconds()
    if attempt == 0 and delta == 0:
        print("Try again")
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
        handshake_status = 'pending'
    elif delta <= 180:
        handshake_status = 'retrying'
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
    msg['Subject'] = 'Wireguard is down'
    msg['From'] = config["user"]
    msg['To'] = config["target"]
    msg['Date'] = utils.formatdate(localtime=True)

    server = smtplib.SMTP_SSL(host=config["host"], port=config["port"], timeout=10)
    # server.set_debuglevel(1)

    server.login(config["user"], config["password"])
    server.sendmail(config["user"], config["target"], msg.as_string())

if __name__ == "__main__":
    config = {
        "target": "noc@freifunk-suedholstein.de",
        "host": "mail.freifunk-suedholstein.de",
        "port": "465",
        "user": sys.argv[1],
        "password": sys.argv[2]
    }
    try:
        if sys.argv[3] == "test":
            print("Sending test mail")
            send_mail(config, "test")    
    except IndexError:
        status = get_health()
        if status != "Health status is ok.":
            send_mail(config, "Host: {}\n{}".format(socket.gethostname(), status))