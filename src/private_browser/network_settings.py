"""Configure the process before Chromium starts; never switch live profiles."""

import os

from PySide6.QtCore import QSettings
from PySide6.QtNetwork import QNetworkProxyFactory


def settings():
    return QSettings("Private Browser", "Private Browser")


def load_network_settings():
    saved = settings()
    mode = saved.value("network/mode", "system")
    if mode not in ("system", "tor"):
        raise ValueError("Invalid saved network mode. Reset network/mode to system or tor.")
    port = int(saved.value("network/tor_port", 9050))
    if not 1 <= port <= 65535:
        raise ValueError("Tor port must be between 1 and 65535.")
    return mode, port


def configure_network(mode, port):
    if mode not in ("system", "tor") or not 1 <= port <= 65535:
        raise ValueError("Invalid network configuration")
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    if mode == "tor":
        # A single explicit proxy, no DIRECT fallback, including loopback URLs.
        # Prevent local DNS lookup for destination names; SOCKS resolves remotely.
        flags += (
            f" --proxy-server=socks5://127.0.0.1:{port}"
            " --proxy-bypass-list=<-loopback>"
            ' --host-resolver-rules="MAP * ~NOTFOUND, EXCLUDE 127.0.0.1"'
            " --disable-quic --force-webrtc-ip-handling-policy=disable_non_proxied_udp"
        )
        # Qt's application-proxy path adds implicit local bypasses. Its system
        # path honors Chromium's explicit proxy preferences, including bypasses.
        QNetworkProxyFactory.setUseSystemConfiguration(True)
    else:
        QNetworkProxyFactory.setUseSystemConfiguration(True)
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags.strip()
