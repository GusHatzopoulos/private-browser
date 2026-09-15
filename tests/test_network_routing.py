"""Test real Chromium routing in fresh processes against local test servers."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROBE = """
import sys
sys.path.insert(0, 'src/private_browser')
from network_settings import configure_network
configure_network('tor', int(sys.argv[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
app = QApplication([])
view = QWebEngineView()
view.loadFinished.connect(lambda ok: (print('LOADED', ok, flush=True), app.quit()))
view.setUrl(QUrl(sys.argv[2]))
QTimer.singleShot(8000, app.quit)
app.exec()
"""


def receive(connection, count):
    result = b""
    while len(result) < count:
        chunk = connection.recv(count - len(result))
        if not chunk:
            raise ConnectionError("Connection closed")
        result += chunk
    return result


class RoutingTests(unittest.TestCase):
    def run_probe(self, port, url, expected_success=False):
        env = os.environ.copy()
        env.pop("QTWEBENGINE_CHROMIUM_FLAGS", None)
        result = subprocess.run(
            [sys.executable, "-c", PROBE, str(port), url], cwd=ROOT,
            env=env, capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"LOADED {expected_success}", result.stdout, result.stdout + result.stderr)

    def test_hostname_is_sent_to_socks_proxy(self):
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen()
            server.settimeout(10)
            hosts = []
            errors = []
            def serve():
                try:
                    connection, _ = server.accept()
                    with connection:
                        connection.settimeout(5)
                        version, count = receive(connection, 2)
                        receive(connection, count)
                        connection.sendall(b"\x05\x00")
                        header = receive(connection, 4)
                        if version != 5 or header[3] != 3:
                            raise ValueError("Expected SOCKS5 domain-name request")
                        size = receive(connection, 1)[0]
                        hosts.append(receive(connection, size).decode())
                        receive(connection, 2)
                        connection.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
                        request = b""
                        while b"\r\n\r\n" not in request:
                            request += receive(connection, 1)
                        body = b"<html><body>SOCKS test page</body></html>"
                        connection.sendall(
                            b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\nContent-Length: "
                            + str(len(body)).encode() + b"\r\n\r\n" + body
                        )
                except Exception as error:
                    errors.append(str(error))
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            self.run_probe(server.getsockname()[1], "http://routing-probe.invalid/", expected_success=True)
            worker.join(10)
            self.assertEqual(errors, [])
            self.assertIn("routing-probe.invalid", hosts)

    def test_dead_proxy_does_not_connect_directly_even_to_loopback(self):
        with socket.socket() as target, socket.socket() as unavailable:
            target.bind(("127.0.0.1", 0))
            target.listen()
            target.settimeout(0.2)
            unavailable.bind(("127.0.0.1", 0))  # Bound, deliberately not listening.
            self.run_probe(unavailable.getsockname()[1], f"http://127.0.0.1:{target.getsockname()[1]}/")
            try:
                connection, _ = target.accept()
            except socket.timeout:
                pass
            else:
                connection.close()
                self.fail("Chromium bypassed the proxy and connected directly")
