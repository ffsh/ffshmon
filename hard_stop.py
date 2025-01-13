import subprocess
import logging


def stop_fastd(service_name):
    """Stop fastd"""
    subprocess.run(
        ["systemctl", "stop", f"fastd@{service_name}.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    logging.info("Stopped fastd service")


# stop wg tunnel
def stop_wg(service_name):
    subprocess.run(
        ["systemctl", "stop", f"wg-quick@{service_name}.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    logging.info("Stopped wireguardw service")
