"""Tests for WireGuard status checks and Prometheus metrics."""

import socket
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from prometheus_client import start_http_server

import wireguard


class WireguardTests(unittest.TestCase):
    """Test the public monitoring behavior without system services."""

    def test_interface_probe_uses_requested_interface(self):
        """The connectivity probe should use the requested interface."""
        curl_result = type("Result", (), {"stdout": '{"mullvad_exit_ip": true}'})()
        with patch("wireguard.subprocess.run", return_value=curl_result) as run:
            self.assertTrue(wireguard.test_interface("wg-test"))

        command = run.call_args.args[0]
        self.assertIn("wg-test", command)

    def test_metrics_endpoint_exposes_cached_status(self):
        """The HTTP endpoint should expose the latest cached gauge value."""
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]

        wireguard.wireguard_up.labels(interface="exit").set(1)
        start_http_server(port, addr="127.0.0.1")

        with urlopen(f"http://127.0.0.1:{port}/metrics") as response:
            metrics = response.read().decode("utf-8")

        self.assertIn('wireguard_up{interface="exit"} 1.0', metrics)


if __name__ == "__main__":
    unittest.main()
