import smtplib
from email.mime.text import MIMEText
from email import utils
import socket
import logging

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