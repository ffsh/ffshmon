import subprocess
import json
import logging
import click
from config_manager import new_config
from hard_stop import stop_fastd, stop_wg
from inform_admin import send_mail


def is_service_running(service_name):
    result = subprocess.run(
        ["systemctl", "show", "-p", "SubState", f"fastd@{service_name}.service"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == "SubState=running"


def test_interface(interface_name):
    """Returns True if interface is ok, returns False if interface is not ok."""
    curl_cmd = [
        "curl",
        "--connect-timeout",
        "10",
        "--interface",
        "exit",
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
        if data["mullvad_exit_ip"] is True:
            logging.info("Everything ok.")
            return True
        else:
            # something went wrong, Mullvad says we are not connected to Mullvad
            logging.error("Mullvad says we are not connected to Mullvad")
            return False
    except KeyError:
        # something went wrong the json did not contain mullvad_exit_ip
        logging.error("mullvad_exit_ip was not in the json")
        return False


def verify(interface_name, fastd_name, mail_config):
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
                "VPN connection did not work, new VPN config did not help.\nFastd and wireguard stopped.",
            )


# Cli group, could add more commands in the future
@click.group()
def cli():
    pass


@cli.command()
@click.option("--user", help="Mail address", required=True)
@click.option("--password", help="Password for Mail Address", required=True)
@click.option("--log", help="Path to log file", required=True)
def check(user, password, log):
    """Check Status of wireguard interface"""

    # Create log file if it does not exist
    try:
        with open(log, "x"):
            # This part will only execute if the file is created successfully
            pass
    except FileExistsError:
        pass

    # Logging Config
    # LogLevel DEBUG, INFO, WARNING, ERROR
    log_level = logging.INFO
    log_format = "%(asctime)s %(levelname)-8s %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        filename=log,
        encoding="utf-8",
        level=log_level,
    )

    # Mail Config
    config = {
        "target": "noc@freifunk-suedholstein.de",
        "host": "mail.freifunk-suedholstein.de",
        "port": "465",
        "user": user,
        "password": password,
    }
    if is_service_running(service_name="ffsh"):
        verify(interface_name="exit", fastd_name="ffsh", mail_config=config)
    else:
        logging.info("Fastd service is down, not checking connection")


if __name__ == "__main__":
    cli()
