"""Regenerate and restart the WireGuard configuration."""

import subprocess
import logging
import time

WG_RESTART_DELAY = 3


def new_config(interface):
    """Regenerate the WireGuard configuration and restart its service."""
    result = subprocess.run(
        ["sudo", "python3", "/opt/wg-conf-gen/wg-conf-gen.py", "recreate"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logging.error("Error while recreating wireguard config:")
        logging.error(result.stdout)
        logging.error(result.stderr)
        logging.error(
            "Failed to recreate wireguard config, restarting wireguard anyway"
        )
    logging.info("Output of wg-conf-gen:")
    logging.info(result.stdout)
    subprocess.run(
        ["sudo", "systemctl", "restart", f"wg-quick@{interface}.service"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    logging.info("Restarted wireguard service")
    # give the interface/handshake time to come up before it gets probed
    time.sleep(WG_RESTART_DELAY)
