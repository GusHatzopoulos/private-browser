from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow


class BrowserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Private Browser")
        self.resize(1280, 800)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://example.com"))

        self.setCentralWidget(self.browser)