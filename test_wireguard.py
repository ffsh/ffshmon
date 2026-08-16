"""Tests for WireGuard status checks and Prometheus metrics."""

import socket
import subprocess
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from click.testing import CliRunner
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
        self.assertEqual(command[0], "curl")
        self.assertIn("wg-test", command)

    def test_interface_probe_retries_after_transient_failure(self):
        """A single failed curl attempt should not fail the probe if a later attempt succeeds."""
        curl_result = type("Result", (), {"stdout": '{"mullvad_exit_ip": true}'})()
        error = subprocess.CalledProcessError(28, ["curl"], stderr="timed out")
        with patch(
            "wireguard.subprocess.run", side_effect=[error, curl_result]
        ) as run:
            with patch("wireguard.time.sleep") as sleep:
                self.assertTrue(wireguard.test_interface("wg-test"))

        self.assertEqual(run.call_count, 2)
        sleep.assert_called_once_with(wireguard.CURL_RETRY_DELAY)

    def test_interface_probe_fails_after_exhausting_retries(self):
        """The probe should give up and return False once all retries fail."""
        error = subprocess.CalledProcessError(28, ["curl"], stderr="timed out")
        with patch(
            "wireguard.subprocess.run", side_effect=[error] * wireguard.CURL_RETRIES
        ) as run:
            with patch("wireguard.time.sleep") as sleep:
                self.assertFalse(wireguard.test_interface("wg-test"))

        self.assertEqual(run.call_count, wireguard.CURL_RETRIES)
        self.assertEqual(sleep.call_count, wireguard.CURL_RETRIES - 1)

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

    def test_serve_accepts_click_options(self):
        """The serve callback should accept options passed by Click."""
        runner = CliRunner()
        with patch("wireguard.configure_logging") as configure_logging:
            with patch("wireguard.start_http_server"):
                with patch("wireguard.run_check", side_effect=KeyboardInterrupt):
                    result = runner.invoke(
                        wireguard.cli,
                        [
                            "serve",
                            "--user",
                            "test@example.org",
                            "--password",
                            "test-password",
                            "--log",
                            "/tmp/ffshmon-test.log",
                        ],
                    )

        self.assertEqual(result.exit_code, 0, result.output)
        configure_logging.assert_called_once_with("/tmp/ffshmon-test.log")


if __name__ == "__main__":
    unittest.main()
