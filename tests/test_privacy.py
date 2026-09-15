import sys
import unittest
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "private_browser"))

from PySide6.QtCore import QUrl
from privacy import RequestBlocker, matches_domain, parse_domains
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWebEngineWidgets import QWebEngineView


class Request:
    def __init__(self, url, first_party="https://example.org/"):
        self.url = QUrl(url)
        self.first_party = QUrl(first_party)
        self.was_blocked = False

    def requestUrl(self):
        return self.url

    def firstPartyUrl(self):
        return self.first_party

    def block(self, blocked):
        self.was_blocked = blocked


class BlockingTests(unittest.TestCase):
    def test_hosts_and_domain_lists(self):
        domains = parse_domains("# list\n0.0.0.0 ads.example.org track.example.org\n127.0.0.1 localhost\nEXAMPLE.NET.\n")
        self.assertEqual(domains, {"ads.example.org", "track.example.org", "example.net"})
        self.assertTrue(matches_domain("a.ads.example.org", domains))
        self.assertFalse(matches_domain("notads.example.org", domains))
        self.assertFalse(matches_domain("ads.example.org.evil.net", domains))

    def test_unsupported_filters_rejected(self):
        for text in ("||example.org^", "example.org##.ad", "https://example.org", "*.example.org"):
            with self.assertRaises(ValueError):
                parse_domains(text)

    def test_blocking_exceptions_and_disable(self):
        blocker = RequestBlocker()
        request = Request("https://sub.doubleclick.net/ad")
        blocker.interceptRequest(request)
        self.assertTrue(request.was_blocked)
        blocker.allowed_sites = frozenset({"example.org"})
        request = Request("https://doubleclick.net/ad")
        blocker.interceptRequest(request)
        self.assertFalse(request.was_blocked)

        request = Request("https://doubleclick.net/ad", "https://another.org")
        blocker.interceptRequest(request)
        self.assertTrue(request.was_blocked)
        blocker.enabled = False
        request = Request("https://doubleclick.net/ad", "https://another.org")
        blocker.interceptRequest(request)
        self.assertFalse(request.was_blocked)


class BlockingIntegrationTests(unittest.TestCase):
    def test_requests_are_blocked_before_reaching_server(self):
        app = QApplication.instance() or QApplication([])
        paths = []
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                paths.append(self.path)
                self.send_response(200)
                self.end_headers()
                try:
                    self.wfile.write(b"ok")
                except ConnectionError:
                    pass

            def log_message(self, *_):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        view = QWebEngineView()
        profile = QWebEngineProfile(view)
        blocker = RequestBlocker(profile)
        blocker.domains = frozenset({"localhost"})
        profile.setUrlRequestInterceptor(blocker)
        page = QWebEnginePage(profile, view)
        view.setPage(page)
        loaded = []
        page.loadFinished.connect(loaded.append)
        port = server.server_port
        try:
            page.setHtml(
                f'<img src="http://localhost:{port}/blocked"><img src="http://127.0.0.1:{port}/allowed">',
                QUrl(f"http://127.0.0.1:{port}/"),
            )
            for _ in range(100):
                QTest.qWait(50)
                if loaded:
                    break
            self.assertTrue(loaded)
            self.assertIn("/allowed", paths)
            self.assertNotIn("/blocked", paths)
        finally:
            page.deleteLater()
            QTest.qWait(50)
            view.deleteLater()
            app.processEvents()
            server.shutdown()
            server.server_close()
