"""Monitor WireGuard connectivity and expose its status to Prometheus."""

import json
import logging
import subprocess
import time
import click
from prometheus_client import Gauge, start_http_server
from config_manager import new_config
from hard_stop import stop_fastd, stop_wg
from inform_admin import send_mail


WIREGUARD_INTERFACE = "exit"
FASTD_SERVICE = "ffsh"
wireguard_up = Gauge(
    "wireguard_up", "Whether the WireGuard connection is up", ["interface"]
)


def is_service_running(service_name):
    """Return whether the configured FastD service is running."""
    result = subprocess.run(
        [
            "sudo",
            "systemctl",
            "show",
            "-p",
            "SubState",
            f"fastd@{service_name}.service",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "SubState=running"


def test_interface(interface_name):
    """Returns True if interface is ok, returns False if interface is not ok."""
    curl_cmd = [
        "curl",
        "--connect-timeout",
        "10",
        "--interface",
        interface_name,
        "https://am.i.mullvad.net/json",
    ]
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        logging.error("Curl could not connect to Mullvad or json was not valid")
        logging.error(e)
        return False
    try:
        connected = data["mullvad_exit_ip"] is True
    except KeyError:
        # something went wrong the json did not contain mullvad_exit_ip
        logging.error("mullvad_exit_ip was not in the json")
        return False

    if connected:
        logging.info("Everything ok.")
        return True

    logging.error("Mullvad says we are not connected to Mullvad")
    return False


def verify(interface_name, fastd_name, mail_config):
    """Check the connection and attempt recovery once if it is down."""
    result = test_interface(interface_name)

    if result is False:
        # connection not ok
        logging.warning("Connection via vpn not ok, generating new config")
        new_config(interface_name)
        result = test_interface(interface_name)
        if result is False:
            logging.error("New config did not help, stop fastd")
            stop_fastd(fastd_name)
            stop_wg(interface_name)
            send_mail(
                mail_config,
                "VPN connection did not work, new VPN config did not help.\n"
                "Fastd and wireguard stopped.",
            )
    return result


def run_check(
    mail_config, interface_name=WIREGUARD_INTERFACE, fastd_name=FASTD_SERVICE
):
    """Run one health cycle and return the resulting up/down state."""
    if is_service_running(service_name=fastd_name):
        return verify(
            interface_name=interface_name,
            fastd_name=fastd_name,
            mail_config=mail_config,
        )

    logging.info("Fastd service is down, not checking connection")
    return False


def configure_logging(log):
    """Create the log file if needed and configure application logging."""
    try:
        with open(log, "x", encoding="utf-8"):
            pass
    except FileExistsError:
        pass

    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=log,
        encoding="utf-8",
        level=logging.INFO,
    )


def build_mail_config(user, password):
    """Build the mail settings used by the recovery alert."""
    return {
        "target": "noc@freifunk-suedholstein.de",
        "host": "mail.freifunk-suedholstein.de",
        "port": "465",
        "user": user,
        "password": password,
    }


@click.group()
def cli():
    """WireGuard monitoring commands."""


@cli.command()
@click.option("--user", help="Mail address", required=True)
@click.option("--password", help="Password for Mail Address", required=True)
@click.option("--log", help="Path to log file", required=True)
def check(user, password, log):
    """Check the status of the WireGuard interface once."""
    configure_logging(log)
    run_check(build_mail_config(user, password))


@cli.command()
@click.option("--user", help="Mail address", required=True)
@click.option("--password", help="Password for Mail Address", required=True)
@click.option("--log", help="Path to log file", required=True)
@click.option("--interval", type=float, default=60.0, show_default=True)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", type=int, default=8000, show_default=True)
def serve(**kwargs):
    """Run checks and expose the latest WireGuard status as Prometheus metrics."""
    user = kwargs["user"]
    password = kwargs["password"]
    log = kwargs["log"]
    interval = kwargs["interval"]
    host = kwargs["host"]
    port = kwargs["port"]
    configure_logging(log)
    start_http_server(port, addr=host)
    config = build_mail_config(user, password)
    try:
        while True:
            wireguard_up.labels(interface=WIREGUARD_INTERFACE).set(
                1 if run_check(config) else 0
            )
            time.sleep(interval)
    except KeyboardInterrupt:
        logging.info("Stopping WireGuard metrics server")


if __name__ == "__main__":
    cli()
