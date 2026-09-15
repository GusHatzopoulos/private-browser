"""Privacy controls with explicit scope and connection status."""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFormLayout, QLabel, QMessageBox, QPushButton, QSpinBox,
)

from network_settings import settings
from privacy import parse_domains


def show_privacy_settings(window):
    dialog = QDialog(window)
    dialog.setWindowTitle("Privacy and connection")
    dialog.setMinimumWidth(480)
    form = QFormLayout(dialog)
    blocker = window.request_blocker
    enabled = QCheckBox("Block known advertising and tracking domains")
    enabled.setChecked(blocker.enabled)
    enabled.toggled.connect(lambda checked: setattr(blocker, "enabled", checked))
    form.addRow(enabled)
    info = QLabel(f"{len(blocker.domains):,} domains · {window.blocked_requests:,} requests blocked in this window")
    form.addRow(info)
    note = QLabel("Blocking and imported lists apply to this window for this session.\nReload pages after changes. Some ads and trackers will remain.")
    note.setWordWrap(True)
    form.addRow(note)

    host = window.current_browser().url().host().lower().rstrip(".")
    allow = QCheckBox(f"Pause blocking on {host or 'this site'}")
    allow.setEnabled(bool(host))
    allow.setChecked(host in blocker.allowed_sites)
    def toggle_site(checked):
        sites = set(blocker.allowed_sites)
        if checked:
            sites.add(host)
        else:
            sites.discard(host)
        blocker.allowed_sites = frozenset(sites)
    allow.toggled.connect(toggle_site)
    form.addRow(allow)
    import_button = QPushButton("Add domains from a hosts / domain file…")
    def import_list():
        filename, _ = QFileDialog.getOpenFileName(dialog, "Import domain list")
        if not filename:
            return
        try:
            path = Path(filename)
            if path.stat().st_size > 20 * 1024 * 1024:
                raise ValueError("List exceeds the 20 MB limit.")
            domains = parse_domains(path.read_text(encoding="utf-8-sig"))
            if not domains:
                raise ValueError("The file contains no domains.")
        except (OSError, UnicodeError, ValueError) as error:
            QMessageBox.warning(dialog, "Could not import list", str(error))
            return
        blocker.domains = blocker.domains | domains
        info.setText(f"{len(blocker.domains):,} domains · list added for this session")
    import_button.clicked.connect(import_list)
    form.addRow(import_button)

    app = QApplication.instance()
    mode = app.property("network_mode") or "system"
    port = app.property("tor_port") or 9050
    current = QLabel(
        f"Current routing: Tor SOCKS proxy at 127.0.0.1:{port} (not verified)"
        if mode == "tor" else "Current routing: system connection (VPN status not verified)"
    )
    current.setWordWrap(True)
    form.addRow(current)
    saved = settings()
    choices = QComboBox()
    choices.addItem("System connection / existing VPN", "system")
    choices.addItem("Local Tor SOCKS proxy", "tor")
    choices.setCurrentIndex(1 if saved.value("network/mode", "system") == "tor" else 0)
    form.addRow("Next startup:", choices)
    port_input = QSpinBox()
    port_input.setRange(1, 65535)
    port_input.setValue(int(saved.value("network/tor_port", 9050)))
    port_input.setEnabled(choices.currentData() == "tor")
    choices.currentIndexChanged.connect(lambda: port_input.setEnabled(choices.currentData() == "tor"))
    form.addRow("Local Tor port:", port_input)
    explanation = QLabel(
        "Tor must already be running locally (usually port 9050, or 9150 for Tor Browser). "
        "If unavailable, pages fail to load; the browser does not switch to a direct connection. "
        "This is not Tor Browser and does not provide its anonymity protections.\n\n"
        "System mode uses your existing network, including an OS VPN if connected. "
        "It does not establish or monitor a VPN tunnel."
    )
    explanation.setWordWrap(True)
    form.addRow(explanation)
    save = QPushButton("Save connection for next startup")
    def save_connection():
        saved.setValue("network/mode", choices.currentData())
        saved.setValue("network/tor_port", port_input.value())
        saved.sync()
        if saved.status() != saved.Status.NoError:
            QMessageBox.warning(dialog, "Settings error", "Could not save connection settings.")
            return
        QMessageBox.information(dialog, "Connection saved", "Close all browser windows and restart. The current connection has not changed.")
    save.clicked.connect(save_connection)
    form.addRow(save)
    check = QPushButton("Open Tor connection check")
    check.setEnabled(mode == "tor")
    check.clicked.connect(lambda: window.add_new_tab(QUrl("https://check.torproject.org/")))
    form.addRow(check)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)
    dialog.exec()
