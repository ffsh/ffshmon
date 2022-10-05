#! python3

import subprocess
import re
import sys
import os
import socket
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email import utils

def test_connection():
    subprocess.run(['curl', '--connect-timeout', '10', '--interface', 'exit', 'https://www.google.com'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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
        print("DNS resolution failed for {}".format(config["host"]))


def create_file_maker(path):
    open(path, mode='a').close()

def remove_file_marker(path):
    if os.path.exists(path):
        os.remove(path)

def check_file_marker(path):
    # returns true if file exists and is not expired else returns false
    if not os.path.exists(path):
        print("File does not exist")
        return False
    else:
        print("File does exist checking timestamp")
        creation_time = datetime.fromtimestamp(os.path.getctime(path))
        # print("DEBUG: creation_time: {}".format(creation_time))
        
        passed_time = creation_time - datetime.now()
        
        print("DEBUG: passed time {}".format(passed_time.total_seconds()))
        
        if abs(passed_time.total_seconds()) >= 14400:
            remove_file_marker(path)
            print("Time has passed, removed file")
            return False
        else: 
            print("Time has not passed, please wait")
            return True

if __name__ == "__main__":
    config = {
        "target": "noc@freifunk-suedholstein.de",
        "host": "mail.freifunk-suedholstein.de",
        "port": "465",
        "user": sys.argv[1],
        "password": sys.argv[2]
    }
    path = "/tmp/ffshmon_marker"

    try:
        if sys.argv[3] == "test":
            print("Sending test mail")
            send_mail(config, "test")    
    except IndexError:
        try:
            test_connection()
            status = get_health()
            if status != "Health status is ok.":
                if not check_file_marker(path):
                    send_mail(config, "Host: {}\n{}".format(socket.gethostname(), status))
                    create_file_maker(path)
                else:
                    print("Not sending mail")
            else:
                print("Status was ok, removing marker")
                remove_file_marker(path)
        except TimeoutError:
            print("Timeout, couldn't send mail.")