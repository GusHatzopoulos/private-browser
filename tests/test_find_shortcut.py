"""Run with: python -m unittest discover -s tests."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "private_browser"))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from browser_window import BrowserWindow


class FindShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.windows = []

    def tearDown(self):
        for window in self.windows:
            window.close()
            window.deleteLater()
        self.app.processEvents()

    def make_window(self):
        window = BrowserWindow()
        self.windows.append(window)
        browser = window.current_browser()
        loaded = []
        browser.loadFinished.connect(loaded.append)
        browser.setHtml("<html><body>needle needle<input autofocus></body></html>")
        window.show()
        window.activateWindow()
        for _ in range(100):
            QTest.qWait(50)
            if loaded and loaded[-1]:
                break
        self.assertTrue(loaded and loaded[-1], "Test page did not load")
        browser.setFocus()
        QTest.qWait(100)
        return window

    def press_find(self):
        target = self.app.focusWidget()
        self.assertIsNotNone(target)
        QTest.keyClick(target, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
        QTest.qWait(50)

    def test_web_content_and_address_bar(self):
        window = self.make_window()
        self.press_find()
        self.assertTrue(window.find_overlay.isVisible())
        self.assertTrue(window.find_overlay.search_box.hasFocus())
        QTest.keyClicks(window.find_overlay.search_box, "needle")
        for _ in range(40):
            QTest.qWait(50)
            if window.find_overlay.result_label.text().endswith("/2"):
                break
        self.assertTrue(window.find_overlay.result_label.text().endswith("/2"))
        QTest.keyClick(window.find_overlay.search_box, Qt.Key.Key_Escape)
        self.assertFalse(window.find_overlay.isVisible())
        window.url_bar.setFocus()
        self.press_find()
        self.assertTrue(window.find_overlay.isVisible())

    def test_only_focused_window_opens_find(self):
        first = self.make_window()
        second = self.make_window()
        self.press_find()
        self.assertTrue(second.find_overlay.isVisible())
        self.assertFalse(first.find_overlay.isVisible())


if __name__ == "__main__":
    unittest.main()
