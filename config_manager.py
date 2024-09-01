import subprocess
import logging

def new_config(interface):
    subprocess.run(['python3', '/opt/wg-conf-gen/wg-conf-gen.py', 'recreate'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info("Recreated wireguard config")
    subprocess.run(['systemctl', 'restart', f'wg-quick@{interface}.service'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logging.info("Restarted wireguard service")