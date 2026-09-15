"""Domain-based request blocking. No browsing history is stored."""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWebEngineCore import QWebEngineUrlRequestInterceptor


def parse_domains(text):
    """Read a plain domain list or hosts file; reject unsupported filter syntax."""
    domains = set()
    for line in text.splitlines():
        if "##" in line and not line.lstrip().startswith("#"):
            raise ValueError("Cosmetic Adblock rules are not supported; use a domain list.")
        fields = line.split("#", 1)[0].strip().lower().split()
        if not fields:
            continue
        if fields[0] in ("0.0.0.0", "127.0.0.1", "::", "::1"):
            fields = fields[1:]
        elif len(fields) != 1:
            raise ValueError("Use a domain list or hosts file, not an Adblock filter list.")
        for value in fields:
            value = value.rstrip(".")
            if value in ("localhost", "localhost.localdomain", "broadcasthost", "ip6-localhost", "ip6-loopback"):
                continue
            try:
                value = value.encode("idna").decode("ascii")
            except UnicodeError as error:
                raise ValueError("Invalid domain in list") from error
            if "." not in value or any(
                not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
                or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in label)
                for label in value.split(".")
            ):
                raise ValueError(f"Unsupported domain entry: {value[:80]}")
            domains.add(value)
    return frozenset(domains)


def matches_domain(host, domains):
    host = host.lower().rstrip(".")
    while host:
        if host in domains:
            return True
        _, separator, host = host.partition(".")
        if not separator:
            break
    return False


class RequestBlocker(QWebEngineUrlRequestInterceptor):
    blocked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.domains = parse_domains(
            Path(__file__).with_name("blocked_domains.txt").read_text(encoding="utf-8")
        )
        self.enabled = True
        self.allowed_sites = frozenset()

    def interceptRequest(self, info):
        if not self.enabled:
            return
        first_party = info.firstPartyUrl().host().lower().rstrip(".")
        if first_party in self.allowed_sites:
            return
        if matches_domain(info.requestUrl().host(), self.domains):
            info.block(True)
            self.blocked.emit()
