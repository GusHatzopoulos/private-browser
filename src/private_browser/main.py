import sys

from PySide6.QtWidgets import QApplication

from network_settings import configure_network, load_network_settings


def main() -> int:
    try:
        mode, port = load_network_settings()
        configure_network(mode, port)
    except (ValueError, TypeError) as error:
        print(f"Cannot start browser: {error}", file=sys.stderr)
        return 1

    from browser_window import BrowserWindow

    app = QApplication(sys.argv)
    app.setProperty("network_mode", mode)
    app.setProperty("tor_port", port)

    app.setApplicationName("Private Browser")
    app.setOrganizationName("Private Browser")

    window = BrowserWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
