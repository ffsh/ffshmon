# ffshmon

`ffshmon` monitors a WireGuard connection and attempts to recover it when the VPN check fails. It checks the configured FastD service, tests the WireGuard interface through Mullvad, regenerates the WireGuard configuration once after a failure, and alerts the NOC if recovery fails.

It also provides a Prometheus endpoint with the latest up/down status.

## Requirements

- Linux with `systemd` and `systemctl`
- Python 3.10 or newer
- `curl`
- A WireGuard interface named `exit` by default
- A FastD service named `fastd@ffsh.service` by default
- `/opt/wg-conf-gen/wg-conf-gen.py` for automatic configuration recovery
- SMTP access to the configured mail host for failure alerts

## Installation

Create a virtual environment and install the Python dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## One-shot check

Run the existing scheduled check with mail credentials and a log file:

```bash
sudo .venv/bin/python wireguard.py check \
  --user noc@example.org \
  --password 'mail-password' \
  --log /var/log/ffshmon.log
```

The command exits after one health cycle. If the FastD service is down, the connection probe is skipped and the status is considered down. If the probe fails, `ffshmon` regenerates the WireGuard configuration and retries once. A second failure stops FastD and WireGuard and sends an email alert.

## Prometheus endpoint

Start the long-running monitor with:

```bash
sudo .venv/bin/python wireguard.py serve \
  --user noc@example.org \
  --password 'mail-password' \
  --log /var/log/ffshmon.log
```

By default, the process:

- Runs an immediate health check, then repeats every 60 seconds.
- Listens on `127.0.0.1:8000`.
- Exposes the latest completed result at `/metrics`.
- Does not run a new health check when Prometheus scrapes the endpoint.

Example request:

```bash
curl http://127.0.0.1:8000/metrics
```

The relevant metric is:

```text
wireguard_up{interface="exit"} 1.0
```

A value of `1` means the latest check succeeded. A value of `0` means the FastD service or WireGuard connectivity check is down.

The listener and polling interval can be changed with `--host`, `--port`, and `--interval`:

```bash
sudo .venv/bin/python wireguard.py serve \
  --user noc@example.org \
  --password 'mail-password' \
  --log /var/log/ffshmon.log \
  --host 127.0.0.1 \
  --port 8000 \
  --interval 60
```

## Prometheus configuration

Add a scrape job for the host running `ffshmon`:

```yaml
scrape_configs:
  - job_name: ffshmon
    static_configs:
      - targets: ["127.0.0.1:8000"]
```

If Prometheus runs on another host, bind `serve` to an appropriate reachable address and protect the endpoint with firewall rules or a reverse proxy. The endpoint has no built-in authentication.

The connectivity probe runs as the service user and does not require `sudo`. The service-management and configuration-recovery commands use `sudo` and must be allowed for the service user without an interactive password prompt.

## Running as a service

Run `serve` as a supervised systemd service so the endpoint remains available. A minimal unit could look like this:

```ini
[Unit]
Description=WireGuard connectivity monitor
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/ffshmon
ExecStart=/opt/ffshmon/.venv/bin/python /opt/ffshmon/wireguard.py serve --user noc@example.org --password mail-password --log /var/log/ffshmon.log
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Avoid storing real credentials directly in a world-readable unit file. Use a protected environment file or another systemd credential mechanism in production.

## Development

Run the focused tests with:

```bash
.venv/bin/python -m unittest -v test_wireguard.py
```

Run Pylint with:

```bash
.venv/bin/python -m pylint wireguard.py test_wireguard.py
```
