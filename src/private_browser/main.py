import sys

from PySide6.QtWidgets import QApplication

from browser_window import BrowserWindow


def main() -> int:
    app = QApplication(sys.argv)

    app.setApplicationName("Private Browser")
    app.setOrganizationName("Private Browser")

    window = BrowserWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())