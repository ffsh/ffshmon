#! python3

import subprocess
import re
from datetime import datetime

def collect():
    result = subprocess.run(['wg', 'show', 'exit', 'latest-handshakes'], stdout=subprocess.PIPE) 
    match = re.search(r"(\d{10,})", result.stdout.decode('utf-8'))
    hand_shake = datetime.now() - datetime.fromtimestamp(int(match[1]))
    delta = hand_shake.total_seconds()
    return delta

def get_status():
    try:
        delta = collect()
    except Exception as e:
        return 'failed'
    if delta <= 120:
        handshake_status = 'ok'
    elif delta <= 135: # 135 is used by the WireGuard reresolve-dns.sh script
        handshake_status = 'pending'
    elif delta <= 180:
        handshake_status = 'retrying'
    else:
        handshake_status = 'failed'
    return handshake_status


def get_health():

    try:
        current_status = status()
    except Exception as e:
        return "Health status is not good, received error: {}".format(e)

    if current_status == "ok":
        return "Health status is ok."
    else:
        return "Health status is {}".format(current_status), 500