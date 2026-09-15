"""Chrome-inspired window controls and styling for the browser shell."""

from PySide6.QtCore import QByteArray, QEvent, QObject, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QMenu, QTabBar, QToolButton


def style_tab(window, index):
    button = QToolButton(window.tab_bar)
    button.setIcon(icon('<path d="m8 8 8 8M16 8l-8 8"/>'))
    button.setFixedSize(20, 20)
    button.setToolTip("Close tab")
    button.setAccessibleName("Close tab")
    button.clicked.connect(lambda: window.close_tab(next(
        (i for i in range(window.tab_bar.count())
         if window.tab_bar.tabButton(i, QTabBar.ButtonPosition.RightSide) is button), -1
    )))
    window.tab_bar.setTabButton(index, QTabBar.ButtonPosition.RightSide, button)


def icon(path: str) -> QIcon:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
        'viewBox="0 0 24 24" fill="none" stroke="#c4c7c5" '
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        f'{path}</svg>'
    )
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


class WindowControls(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        window.tab_strip.installEventFilter(self)
        window.tab_bar.installEventFilter(self)
        window.browser_shell.installEventFilter(self)

    def toggle_maximized(self):
        if self.window.isMaximized():
            self.window.showNormal()
        else:
            self.window.showMaximized()

    def eventFilter(self, watched, event):
        window = self.window
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            handle = window.windowHandle()
            if handle is None:
                return False
            if watched is window.browser_shell and not window.isMaximized():
                point = event.position().toPoint()
                edges = Qt.Edge(0)
                if point.x() < 5:
                    edges |= Qt.Edge.LeftEdge
                if point.x() >= watched.width() - 5:
                    edges |= Qt.Edge.RightEdge
                if point.y() < 5:
                    edges |= Qt.Edge.TopEdge
                if point.y() >= watched.height() - 5:
                    edges |= Qt.Edge.BottomEdge
                if edges:
                    return handle.startSystemResize(edges)
            elif watched is window.tab_strip or (
                watched is window.tab_bar and window.tab_bar.tabAt(event.position().toPoint()) < 0
            ):
                return handle.startSystemMove()
        if event.type() == QEvent.Type.MouseButtonDblClick:
            if watched is window.tab_strip or (
                watched is window.tab_bar and window.tab_bar.tabAt(event.position().toPoint()) < 0
            ):
                self.toggle_maximized()
                return True
        return super().eventFilter(watched, event)


def apply_chrome_ui(window):
    window.setWindowFlag(Qt.WindowType.FramelessWindowHint)
    window.setMinimumSize(640, 360)
    window.browser_layout.setContentsMargins(5, 5, 5, 5)
    window.tab_strip.setFixedHeight(35)
    window.tab_strip_layout.setContentsMargins(3, 0, 0, 0)
    window.navigation_widget.setFixedHeight(48)
    window.navigation_layout.setContentsMargins(6, 5, 8, 5)
    window.navigation_layout.setSpacing(6)
    window.url_bar.setFixedHeight(36)
    window.url_bar.setClearButtonEnabled(False)
    window.url_bar.setPlaceholderText("Search DuckDuckGo or enter address")
    window.tab_bar.setElideMode(Qt.TextElideMode.ElideRight)
    window.tab_bar.setDrawBase(False)

    window.window_controls = WindowControls(window)
    controls = window.window_controls
    for name, drawing, callback in (
        ("Minimize", '<path d="M6 12h12"/>', window.showMinimized),
        ("Maximize / Restore", '<rect x="7" y="7" width="10" height="10" rx="1"/>', controls.toggle_maximized),
        ("Close", '<path d="m7 7 10 10M17 7 7 17"/>', window.close),
    ):
        button = QToolButton(window.tab_strip)
        button.setObjectName("closeWindowButton" if name == "Close" else "windowButton")
        button.setIcon(icon(drawing))
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(46, 34)
        button.setToolTip(name)
        button.setAccessibleName(name)
        button.clicked.connect(callback)
        window.tab_strip_layout.addWidget(button)

    for button, drawing in (
        (window.back_button, '<path d="m14 6-6 6 6 6M8 12h12"/>'),
        (window.forward_button, '<path d="m10 6 6 6-6 6M4 12h12"/>'),
        (window.reload_button, '<path d="M19 10a7 7 0 1 0-1 7M19 4v6h-6"/>'),
        (window.home_button, '<path d="m4 11 8-7 8 7M6 10v10h12V10M10 20v-7h4v7"/>'),
        (window.new_tab_button, '<path d="M12 6v12M6 12h12"/>'),
    ):
        button.setText("")
        button.setIcon(icon(drawing))
        button.setIconSize(QSize(18, 18))
        button.setAccessibleName(button.toolTip())

    window.url_bar.addAction(
        icon('<path d="M4 8h16M4 16h16"/><circle cx="9" cy="8" r="2" fill="#303134"/><circle cx="15" cy="16" r="2" fill="#303134"/>'),
        window.url_bar.ActionPosition.LeadingPosition,
    ).setEnabled(False)

    menu_button = QToolButton()
    menu_button.setObjectName("navigationButton")
    menu_button.setIcon(icon('<circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/>'))
    menu_button.setToolTip("Browser menu")
    menu_button.setAccessibleName("Browser menu")
    menu_button.setFixedSize(32, 32)
    menu = QMenu(menu_button)
    menu.addAction("New tab", lambda: window.add_new_tab())
    menu.addAction("New window", window.create_new_window)
    menu.addSeparator()
    menu.addAction("Find in page", window.show_find_overlay)
    menu.addAction("Reload", window.reload_page)
    menu.addSeparator()
    menu.addAction("Close window", window.close)
    menu_button.setMenu(menu)
    menu_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    window.navigation_layout.addWidget(menu_button)

    window.setStyleSheet(window.styleSheet() + """
        QMainWindow, QWidget#browserShell, QWidget#tabStrip { background: #202124; }
        QTabBar#browserTabBar { background: transparent; border: none; }
        QWidget#navigationBar { background: #353638; }
        QTabBar#browserTabBar::tab {
            background: #202124; color: #bdc1c6;
            min-width: 140px; max-width: 220px; height: 32px;
            padding: 0px 12px; margin: 3px 2px 0px 0px;
            border-top-left-radius: 10px; border-top-right-radius: 10px;
        }
        QTabBar#browserTabBar::tab:selected { background: #353638; color: #e8eaed; }
        QTabBar#browserTabBar::tab:hover:!selected { background: #2c2d30; }
        QLineEdit#addressBar {
            background: #202124; border: 2px solid transparent;
            border-radius: 18px; padding: 0px 10px; font-size: 13px;
        }
        QLineEdit#addressBar:hover { background: #292a2d; }
        QLineEdit#addressBar:focus { background: #303134; border: 2px solid #a8c7fa; }
        QToolButton#windowButton, QToolButton#closeWindowButton {
            background: transparent; border: none; border-radius: 0px;
        }
        QToolButton#windowButton:hover { background: #3c4043; }
        QToolButton#closeWindowButton:hover { background: #c42b1c; }
        QToolButton#navigationButton::menu-indicator { image: none; }
        QMenu { background: #292a2d; color: #e8eaed; border: 1px solid #5f6368; padding: 6px; }
        QMenu::item { padding: 8px 28px 8px 16px; }
        QMenu::item:selected { background: #3c4043; border-radius: 4px; }
        QMenu::separator { height: 1px; background: #45474a; margin: 4px; }
    """)
