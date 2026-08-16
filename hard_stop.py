"""Stop the FastD and WireGuard services during failed recovery."""

import subprocess
import logging


def stop_fastd(service_name):
    """Stop fastd"""
    subprocess.run(
        ["sudo", "systemctl", "stop", f"fastd@{service_name}.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    logging.info("Stopped fastd service")


# stop wg tunnel
def stop_wg(service_name):
    """Stop the WireGuard service for the configured interface."""
    subprocess.run(
        ["sudo", "systemctl", "stop", f"wg-quick@{service_name}.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    logging.info("Stopped wireguardw service")
