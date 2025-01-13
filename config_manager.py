import subprocess
import logging

def new_config(interface):
    result = subprocess.run(
        ['python3', '/opt/wg-conf-gen/wg-conf-gen.py', 'recreate'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        logging.error("Error while recreating wireguard config:")
        logging.error(result.stdout)
        logging.error(result.stderr)
        logging.error("Failed to recreate wireguard config, restarting wireguard anyway")
    subprocess.run(['systemctl', 'restart', f'wg-quick@{interface}.service'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
    logging.info("Restarted wireguard service")