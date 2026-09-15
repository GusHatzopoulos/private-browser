from urllib.parse import quote_plus

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QLineEdit,
    QMainWindow,
    QToolBar,
)


class AddressBar(QLineEdit):
    def __init__(self) -> None:
        super().__init__()
        self._select_all_on_click = True

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)

        if self._select_all_on_click:
            QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event) -> None:
        had_focus = self.hasFocus()

        super().mousePressEvent(event)

        if not had_focus:
            QTimer.singleShot(0, self.selectAll)


class BrowserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("Private Browser")
        self.resize(1280, 800)

        # Browser view
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://example.com"))
        self.setCentralWidget(self.browser)

        # Navigation toolbar
        self.navigation_bar = QToolBar("Navigation")
        self.addToolBar(self.navigation_bar)

        # Back
        back_action = self.navigation_bar.addAction("←")
        back_action.triggered.connect(self.browser.back)

        # Forward
        forward_action = self.navigation_bar.addAction("→")
        forward_action.triggered.connect(self.browser.forward)

        # Reload
        reload_action = self.navigation_bar.addAction("↻")
        reload_action.triggered.connect(self.browser.reload)

        # Home
        home_action = self.navigation_bar.addAction("⌂")
        home_action.triggered.connect(self.go_home)

        # Address / search bar
        self.url_bar = AddressBar()
        self.url_bar.setPlaceholderText("Search or enter address")
        self.url_bar.setClearButtonEnabled(True)

        self.navigation_bar.addWidget(self.url_bar)

        # Navigate when Enter is pressed
        self.url_bar.returnPressed.connect(self.navigate_to_url)

        # Keep address bar synchronized
        self.browser.urlChanged.connect(self.update_url_bar)

        # Keyboard shortcuts
        self.reload_shortcut = QShortcut(QKeySequence("F5"), self)
        self.reload_shortcut.activated.connect(self.browser.reload)

        self.back_shortcut = QShortcut(QKeySequence("Backspace"), self)
        self.back_shortcut.activated.connect(self.go_back_with_keyboard)

    def navigate_to_url(self) -> None:
        text = self.url_bar.text().strip()

        if not text:
            return

        # Explicit URL
        if text.startswith(("http://", "https://")):
            url = QUrl(text)

        # Looks like a domain
        elif "." in text and " " not in text:
            url = QUrl("https://" + text)

        # Otherwise treat input as a search query
        else:
            query = quote_plus(text)
            url = QUrl(f"https://duckduckgo.com/?q={query}")

        self.browser.setUrl(url)

    def update_url_bar(self, url: QUrl) -> None:
        self.url_bar.setText(url.toString())
        self.url_bar.setCursorPosition(0)

    def go_home(self) -> None:
        self.browser.setUrl(QUrl("https://example.com"))

    def go_back_with_keyboard(self) -> None:
        if self.url_bar.hasFocus():
            return

        self.browser.back()