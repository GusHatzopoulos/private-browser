from pathlib import Path
from urllib.parse import quote_plus

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


HOME_URL = "https://example.com"


# ============================================================
# Address Bar
# ============================================================


class AddressBar(QLineEdit):
    """Browser-style address/search bar."""

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

    def mousePressEvent(self, event) -> None:
        had_focus = self.hasFocus()

        super().mousePressEvent(event)

        if not had_focus:
            QTimer.singleShot(0, self.selectAll)


# ============================================================
# Chrome-style Find Overlay
# ============================================================


class FindOverlay(QWidget):
    WIDTH = 360
    HEIGHT = 46

    def __init__(
        self,
        browser_window: "BrowserWindow",
    ) -> None:
        super().__init__(browser_window.tabs)

        self.browser_window = browser_window

        self.setFixedSize(
            self.WIDTH,
            self.HEIGHT,
        )

        self.setObjectName("findOverlay")

        self.setAttribute(
            Qt.WidgetAttribute.WA_StyledBackground,
            True,
        )

        self.setStyleSheet(
            """
            QWidget#findOverlay {
                background-color: #292929;
                border: 1px solid #454545;
                border-radius: 8px;
            }

            QLineEdit {
                background-color: #292929;
                color: #ffffff;
                border: none;
                padding: 5px 6px;
                selection-background-color: #3d6ea8;
                selection-color: #ffffff;
            }

            QLabel {
                background-color: #292929;
                color: #dddddd;
                padding-left: 5px;
                padding-right: 5px;
            }

            QPushButton {
                background-color: #292929;
                color: #ffffff;
                border: none;
                min-width: 28px;
                min-height: 28px;
                border-radius: 4px;
            }

            QPushButton:hover {
                background-color: #3a3a3a;
            }

            QPushButton:pressed {
                background-color: #444444;
            }
            """
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            12,
            6,
            8,
            6,
        )

        layout.setSpacing(4)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Find")

        self.result_label = QLabel("")

        self.previous_button = QPushButton("↑")
        self.next_button = QPushButton("↓")
        self.close_button = QPushButton("×")

        self.previous_button.setToolTip(
            "Previous match (Shift+Enter)"
        )

        self.next_button.setToolTip(
            "Next match (Enter)"
        )

        self.close_button.setToolTip(
            "Close (Esc)"
        )

        layout.addWidget(
            self.search_box,
            1,
        )

        layout.addWidget(
            self.result_label,
        )

        layout.addWidget(
            self.previous_button,
        )

        layout.addWidget(
            self.next_button,
        )

        layout.addWidget(
            self.close_button,
        )

        self.search_box.textChanged.connect(
            self.search_live
        )

        self.previous_button.clicked.connect(
            self.find_previous
        )

        self.next_button.clicked.connect(
            self.find_next
        )

        self.close_button.clicked.connect(
            self.close_overlay
        )

        self.search_box.installEventFilter(
            self
        )

        self.hide()

    # --------------------------------------------------------
    # Current Browser
    # --------------------------------------------------------

    def browser(self) -> "BrowserView | None":
        return self.browser_window.current_browser()

    # --------------------------------------------------------
    # Open / Close
    # --------------------------------------------------------

    def open_overlay(self) -> None:
        self.browser_window.position_find_overlay()

        self.show()
        self.raise_()

        self.search_box.setFocus()
        self.search_box.selectAll()

        if self.search_box.text():
            self.search_live(
                self.search_box.text()
            )

    def close_overlay(self) -> None:
        browser = self.browser()

        if browser is not None:
            browser.findText("")

        self.result_label.clear()

        self.hide()

        if browser is not None:
            browser.setFocus()

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    def search_live(
        self,
        text: str,
    ) -> None:
        browser = self.browser()

        if browser is None:
            return

        if not text:
            browser.findText("")
            self.result_label.clear()
            return

        browser.findText(
            text,
            QWebEnginePage.FindFlag(0),
            self.update_result,
        )

    def find_next(self) -> None:
        browser = self.browser()
        text = self.search_box.text()

        if browser is None or not text:
            return

        browser.findText(
            text,
            QWebEnginePage.FindFlag(0),
            self.update_result,
        )

    def find_previous(self) -> None:
        browser = self.browser()
        text = self.search_box.text()

        if browser is None or not text:
            return

        browser.findText(
            text,
            QWebEnginePage.FindFlag.FindBackward,
            self.update_result,
        )

    def update_result(
        self,
        result,
    ) -> None:
        total = result.numberOfMatches()
        active = result.activeMatch()

        if total <= 0:
            self.result_label.setText("0/0")
            return

        self.result_label.setText(
            f"{active}/{total}"
        )

    # --------------------------------------------------------
    # Keyboard
    # --------------------------------------------------------

    def eventFilter(
        self,
        watched,
        event,
    ) -> bool:
        if (
            watched is self.search_box
            and event.type()
            == QEvent.Type.KeyPress
        ):
            key = event.key()

            if key == Qt.Key.Key_Escape:
                self.close_overlay()
                return True

            if key in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                if (
                    event.modifiers()
                    & Qt.KeyboardModifier.ShiftModifier
                ):
                    self.find_previous()
                else:
                    self.find_next()

                return True

        return super().eventFilter(
            watched,
            event,
        )


# ============================================================
# Browser View
# ============================================================


class BrowserView(QWebEngineView):
    """One WebEngine view = one browser tab."""

    def __init__(
        self,
        browser_window: "BrowserWindow",
        profile: QWebEngineProfile,
    ) -> None:
        super().__init__()

        self.browser_window = browser_window

        page = QWebEnginePage(
            profile,
            self,
        )

        self.setPage(page)

    def createWindow(
        self,
        window_type: QWebEnginePage.WebWindowType,
    ) -> QWebEngineView:
        # Open link in new window
        if (
            window_type
            == QWebEnginePage.WebWindowType.WebBrowserWindow
        ):
            new_window = (
                self.browser_window.create_new_window()
            )

            browser = new_window.current_browser()

            if browser is not None:
                return browser

        # Open link in new tab / background tab / popup.
        return self.browser_window.add_new_tab(
            QUrl("about:blank"),
            "New Tab",
        )


# ============================================================
# Browser Window
# ============================================================


class BrowserWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.child_windows: list[BrowserWindow] = []

        self.setWindowTitle(
            "Private Browser"
        )

        self.resize(
            1280,
            800,
        )

        # ====================================================
        # WebEngine Profile
        # ====================================================

        self.profile = QWebEngineProfile(self)

        self.profile.downloadRequested.connect(
            self.handle_download
        )

        # ====================================================
        # Main Browser Shell
        # ====================================================

        self.browser_shell = QWidget()
        self.browser_shell.setObjectName(
            "browserShell"
        )

        self.browser_layout = QVBoxLayout(
            self.browser_shell
        )

        self.browser_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.browser_layout.setSpacing(0)

        self.setCentralWidget(
            self.browser_shell
        )

        # ====================================================
        # Tabs
        # ====================================================

        self.tabs = QTabWidget()

        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)

        self.tabs.tabCloseRequested.connect(
            self.close_tab
        )

        self.tabs.currentChanged.connect(
            self.current_tab_changed
        )

        # ====================================================
        # Custom Navigation Bar
        # ====================================================

        self.navigation_widget = QWidget()
        self.navigation_widget.setObjectName(
            "navigationBar"
        )

        self.navigation_layout = QHBoxLayout(
            self.navigation_widget
        )

        self.navigation_layout.setContentsMargins(
            8,
            5,
            8,
            5,
        )

        self.navigation_layout.setSpacing(5)

        # Back
        self.back_button = QToolButton()
        self.back_button.setText("←")
        self.back_button.setToolTip("Back")

        self.back_button.clicked.connect(
            self.go_back
        )

        # Forward
        self.forward_button = QToolButton()
        self.forward_button.setText("→")
        self.forward_button.setToolTip(
            "Forward"
        )

        self.forward_button.clicked.connect(
            self.go_forward
        )

        # Reload
        self.reload_button = QToolButton()
        self.reload_button.setText("↻")
        self.reload_button.setToolTip(
            "Reload (F5)"
        )

        self.reload_button.clicked.connect(
            self.reload_page
        )

        # Home
        self.home_button = QToolButton()
        self.home_button.setText("⌂")
        self.home_button.setToolTip(
            "Home"
        )

        self.home_button.clicked.connect(
            self.go_home
        )

        # Address / Search
        self.url_bar = AddressBar()

        self.url_bar.setPlaceholderText(
            "Search or enter address"
        )

        self.url_bar.setClearButtonEnabled(
            True
        )

        self.url_bar.returnPressed.connect(
            self.navigate_to_url
        )

        self.navigation_layout.addWidget(
            self.back_button
        )

        self.navigation_layout.addWidget(
            self.forward_button
        )

        self.navigation_layout.addWidget(
            self.reload_button
        )

        self.navigation_layout.addWidget(
            self.home_button
        )

        self.navigation_layout.addWidget(
            self.url_bar,
            1,
        )

        # ====================================================
        # Add shell components
        #
        # QTabWidget normally owns its tab bar AND page area.
        # We therefore use its native tab bar and place the
        # navigation widget visually over the top of the page
        # using a layout wrapper below.
        # ====================================================

        self.content_wrapper = QWidget()

        self.content_layout = QVBoxLayout(
            self.content_wrapper
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.content_layout.setSpacing(0)

        # Tabs contain the actual BrowserView pages.
        self.content_layout.addWidget(
            self.tabs,
            1,
        )

        self.browser_layout.addWidget(
            self.navigation_widget
        )

        self.browser_layout.addWidget(
            self.content_wrapper,
            1,
        )

        # ====================================================
        # New Tab Button
        # ====================================================

        self.new_tab_button = QToolButton()

        self.new_tab_button.setText("+")
        self.new_tab_button.setToolTip(
            "New Tab (Ctrl+T)"
        )

        self.new_tab_button.setFixedSize(
            34,
            30,
        )

        self.new_tab_button.clicked.connect(
            self.add_new_tab
        )

        self.tabs.setCornerWidget(
            self.new_tab_button,
            Qt.Corner.TopRightCorner,
        )

        # ====================================================
        # Find Overlay
        # ====================================================

        self.find_overlay = FindOverlay(
            self
        )

        # ====================================================
        # Keyboard Shortcuts
        # ====================================================

        self.new_tab_shortcut = QShortcut(
            QKeySequence("Ctrl+T"),
            self,
        )

        self.new_tab_shortcut.activated.connect(
            self.add_new_tab
        )

        self.close_tab_shortcut = QShortcut(
            QKeySequence("Ctrl+W"),
            self,
        )

        self.close_tab_shortcut.activated.connect(
            self.close_current_tab
        )

        self.new_window_shortcut = QShortcut(
            QKeySequence("Ctrl+N"),
            self,
        )

        self.new_window_shortcut.activated.connect(
            self.create_new_window
        )

        self.focus_url_shortcut = QShortcut(
            QKeySequence("Ctrl+L"),
            self,
        )

        self.focus_url_shortcut.activated.connect(
            self.focus_url_bar
        )

        # Ctrl+F must use ApplicationShortcut because
        # Chromium/WebEngine can otherwise consume it.
        self.find_shortcut = QShortcut(
            QKeySequence.StandardKey.Find,
            self,
        )

        self.find_shortcut.setContext(
            Qt.ShortcutContext.ApplicationShortcut
        )

        self.find_shortcut.activated.connect(
            self.show_find_overlay
        )

        self.reload_shortcut = QShortcut(
            QKeySequence("F5"),
            self,
        )

        self.reload_shortcut.activated.connect(
            self.reload_page
        )

        self.back_shortcut = QShortcut(
            QKeySequence("Backspace"),
            self,
        )

        self.back_shortcut.activated.connect(
            self.go_back_with_keyboard
        )

        # ====================================================
        # Chromium-style Dark UI
        # ====================================================

        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #202124;
            }

            QWidget#browserShell {
                background-color: #202124;
            }

            QWidget#navigationBar {
                background-color: #2b2c2f;
                border: none;
            }

            QTabWidget::pane {
                border: none;
                background-color: #202124;
            }

            QTabBar {
                background-color: #202124;
                border: none;
            }

            QTabBar::tab {
                background-color: #202124;
                color: #cfcfcf;

                min-width: 150px;
                max-width: 230px;
                height: 34px;

                padding-left: 12px;
                padding-right: 10px;

                margin-top: 4px;
                margin-right: 2px;

                border: none;

                border-top-left-radius: 9px;
                border-top-right-radius: 9px;
            }

            QTabBar::tab:selected {
                background-color: #2b2c2f;
                color: #ffffff;
            }

            QTabBar::tab:hover:!selected {
                background-color: #292a2d;
            }

            QWidget#navigationBar QToolButton {
                background-color: transparent;
                color: #e8eaed;

                border: none;
                border-radius: 16px;

                min-width: 32px;
                max-width: 32px;

                min-height: 32px;
                max-height: 32px;

                font-size: 16px;
            }

            QWidget#navigationBar QToolButton:hover {
                background-color: #3c4043;
            }

            QWidget#navigationBar QToolButton:pressed {
                background-color: #45494c;
            }

            QWidget#navigationBar QLineEdit {
                background-color: #202124;
                color: #e8eaed;

                border: 1px solid transparent;
                border-radius: 17px;

                min-height: 32px;
                max-height: 32px;

                padding-left: 13px;
                padding-right: 13px;

                selection-background-color: #3f6594;
                selection-color: #ffffff;
            }

            QWidget#navigationBar QLineEdit:focus {
                background-color: #202124;
                border: 1px solid #5f6368;
            }

            QTabWidget QToolButton {
                background-color: transparent;
                color: #e8eaed;

                border: none;
                border-radius: 14px;
            }

            QTabWidget QToolButton:hover {
                background-color: #3c4043;
            }
            """
        )

        # ====================================================
        # First Tab
        # ====================================================

        self.add_new_tab(
            QUrl(HOME_URL),
            "New Tab",
        )

    # ========================================================
    # Current Browser
    # ========================================================

    def current_browser(
        self,
    ) -> BrowserView | None:
        widget = self.tabs.currentWidget()

        if isinstance(
            widget,
            BrowserView,
        ):
            return widget

        return None

    # ========================================================
    # Tabs
    # ========================================================

    def add_new_tab(
        self,
        url: QUrl | None = None,
        label: str = "New Tab",
    ) -> BrowserView:
        if url is None:
            url = QUrl(
                "about:blank"
            )

        browser = BrowserView(
            self,
            self.profile,
        )

        index = self.tabs.addTab(
            browser,
            label,
        )

        self.tabs.setCurrentIndex(
            index
        )

        browser.urlChanged.connect(
            lambda new_url, browser=browser:
            self.update_url_bar(
                new_url,
                browser,
            )
        )

        browser.titleChanged.connect(
            lambda title, browser=browser:
            self.update_tab_title(
                title,
                browser,
            )
        )

        browser.setUrl(url)

        return browser

    def close_tab(
        self,
        index: int,
    ) -> None:
        if self.tabs.count() == 1:
            return

        widget = self.tabs.widget(
            index
        )

        self.tabs.removeTab(
            index
        )

        if widget is not None:
            widget.deleteLater()

        self.position_find_overlay()

    def close_current_tab(
        self,
    ) -> None:
        self.close_tab(
            self.tabs.currentIndex()
        )

    def current_tab_changed(
        self,
        index: int,
    ) -> None:
        browser = self.current_browser()

        if browser is None:
            return

        self.url_bar.setText(
            browser.url().toString()
        )

        self.url_bar.setCursorPosition(
            0
        )

        title = browser.title()

        if title:
            self.setWindowTitle(
                f"{title} - Private Browser"
            )
        else:
            self.setWindowTitle(
                "Private Browser"
            )

        if self.find_overlay.isVisible():
            text = (
                self.find_overlay
                .search_box
                .text()
            )

            self.find_overlay.search_live(
                text
            )

            self.position_find_overlay()

    def update_tab_title(
        self,
        title: str,
        browser: BrowserView,
    ) -> None:
        index = self.tabs.indexOf(
            browser
        )

        if index == -1:
            return

        if not title:
            title = "New Tab"

        display_title = title

        if len(display_title) > 30:
            display_title = (
                display_title[:27]
                + "..."
            )

        self.tabs.setTabText(
            index,
            display_title,
        )

        if browser == self.current_browser():
            self.setWindowTitle(
                f"{title} - Private Browser"
            )

    # ========================================================
    # New Window
    # ========================================================

    def create_new_window(
        self,
    ) -> "BrowserWindow":
        new_window = BrowserWindow()

        self.child_windows.append(
            new_window
        )

        new_window.show()

        return new_window

    # ========================================================
    # Address / Search
    # ========================================================

    def navigate_to_url(
        self,
    ) -> None:
        text = (
            self.url_bar
            .text()
            .strip()
        )

        if not text:
            return

        if text.startswith(
            (
                "http://",
                "https://",
            )
        ):
            url = QUrl(text)

        elif text.startswith(
            "about:"
        ):
            url = QUrl(text)

        elif (
            "." in text
            and " " not in text
        ):
            url = QUrl(
                "https://" + text
            )

        else:
            query = quote_plus(
                text
            )

            url = QUrl(
                "https://duckduckgo.com/"
                f"?q={query}"
            )

        browser = self.current_browser()

        if browser is not None:
            browser.setUrl(url)

    def update_url_bar(
        self,
        url: QUrl,
        browser: BrowserView,
    ) -> None:
        if (
            browser
            != self.current_browser()
        ):
            return

        self.url_bar.setText(
            url.toString()
        )

        self.url_bar.setCursorPosition(
            0
        )

    def focus_url_bar(
        self,
    ) -> None:
        self.url_bar.setFocus()
        self.url_bar.selectAll()

    # ========================================================
    # Navigation
    # ========================================================

    def go_back(self) -> None:
        browser = self.current_browser()

        if browser is not None:
            browser.back()

    def go_forward(self) -> None:
        browser = self.current_browser()

        if browser is not None:
            browser.forward()

    def reload_page(self) -> None:
        browser = self.current_browser()

        if browser is not None:
            browser.reload()

    def go_home(self) -> None:
        browser = self.current_browser()

        if browser is not None:
            browser.setUrl(
                QUrl(HOME_URL)
            )

    def go_back_with_keyboard(
        self,
    ) -> None:
        # Never navigate backwards while the user
        # is editing our browser UI.
        if self.url_bar.hasFocus():
            return

        if (
            self.find_overlay
            .search_box
            .hasFocus()
        ):
            return

        self.go_back()

    # ========================================================
    # Find Overlay
    # ========================================================

    def show_find_overlay(
        self,
    ) -> None:
        self.find_overlay.open_overlay()

    def position_find_overlay(
        self,
    ) -> None:
        if not hasattr(
            self,
            "find_overlay",
        ):
            return

        parent_width = (
            self.tabs.width()
        )

        margin = 12

        x = (
            parent_width
            - self.find_overlay.width()
            - margin
        )

        tab_bar_height = (
            self.tabs
            .tabBar()
            .height()
        )

        y = (
            tab_bar_height
            + margin
        )

        x = max(
            margin,
            x,
        )

        self.find_overlay.move(
            x,
            y,
        )

        if self.find_overlay.isVisible():
            self.find_overlay.raise_()

    # ========================================================
    # Downloads / Save Link / Save Page
    # ========================================================

    def handle_download(
        self,
        download,
    ) -> None:
        suggested_name = (
            download
            .suggestedFileName()
        )

        if not suggested_name:
            suggested_name = "download"

        downloads_folder = (
            Path.home()
            / "Downloads"
        )

        suggested_path = (
            downloads_folder
            / suggested_name
        )

        file_path, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Save File",
                str(
                    suggested_path
                ),
            )
        )

        if not file_path:
            download.cancel()
            return

        destination = Path(
            file_path
        )

        download.setDownloadDirectory(
            str(
                destination.parent
            )
        )

        download.setDownloadFileName(
            destination.name
        )

        download.accept()

    # ========================================================
    # Window Events
    # ========================================================

    def resizeEvent(
        self,
        event,
    ) -> None:
        super().resizeEvent(
            event
        )

        self.position_find_overlay()