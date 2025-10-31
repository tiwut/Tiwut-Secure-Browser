#!/usr/bin/env python3

import sys
import configparser
import os
import sqlite3
import webbrowser
from PyQt5.QtCore import QUrl, Qt, QSize
from PyQt5.QtWidgets import (QApplication, QMainWindow, QToolBar, QLineEdit,
                             QPushButton, QDialog, QFormLayout, QCheckBox,
                             QLabel, QDialogButtonBox, QTabWidget, QStatusBar,
                             QProgressBar, QMenu, QVBoxLayout, QComboBox,
                             QListWidget, QListWidgetItem, QAction, QFileDialog,
                             QHBoxLayout, QWidget)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineProfile, QWebEngineDownloadItem
from PyQt5.QtGui import QIcon

FINAL_DARK_STYLE = """
    /* ... (vorheriger Style) ... */
    QMainWindow, QDialog { background-color: #1c1c1c; } QToolBar { background-color: #2a2a2a; border: none; padding: 6px; spacing: 6px; } QLineEdit { background-color: #3c3c3c; border: 1px solid #555; border-radius: 18px; padding: 8px 18px; color: #e0e0e0; font-size: 15px; } QLineEdit:focus { border: 1px solid #007bff; } QPushButton { background-color: #3c3c3c; color: #e0e0e0; border: none; padding: 9px 18px; border-radius: 18px; font-weight: bold; } QPushButton:hover { background-color: #4a4a4a; } QPushButton:pressed { background-color: #007bff; } QPushButton#TiwutButton { color: #fff; background-color: #28a745; } QPushButton#TiwutButton:hover { background-color: #218838; } QLabel, QCheckBox { color: #e0e0e0; font-size: 14px; } QStatusBar { color: #e0e0e0; } QProgressBar { border-radius: 5px; text-align: center; } QProgressBar::chunk { background-color: #007bff; border-radius: 5px; } QTabWidget::pane { border: none; } QTabBar::tab { background: #2a2a2a; color: #aaa; padding: 10px 20px; border-top-left-radius: 10px; border-top-right-radius: 10px; min-width: 120px; } QTabBar::tab:selected { background: #3c3c3c; color: #fff; } QTabBar::tab:hover { background: #4a4a4a; } 
    QTabBar::close-button {
        /* NEU: Erzwingt das Icon */
        image: url(./icons/close.png);
        background: transparent;
        border-radius: 8px;
        padding: 2px;
    }
    QTabBar::close-button:hover { background: #555; }
    QListWidget { background-color: #3c3c3c; border: 1px solid #555; color: #e0e0e0; }
"""

class DatabaseManager:
    def __init__(self, db_name="browser_data.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()
    def create_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS bookmarks (id INTEGER PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL, UNIQUE(url))")
        self.conn.commit()
    def add_history_entry(self, url, title):
        if url.startswith("https://www.google.com/search?q="): return
        self.cursor.execute("INSERT INTO history (url, title) VALUES (?, ?)", (url, title))
        self.conn.commit()
    def get_history(self):
        self.cursor.execute("SELECT title, url FROM history ORDER BY timestamp DESC LIMIT 100")
        return self.cursor.fetchall()
    def clear_history(self):
        self.cursor.execute("DELETE FROM history"); self.conn.commit()
    def add_bookmark(self, url, title):
        self.cursor.execute("INSERT OR IGNORE INTO bookmarks (url, title) VALUES (?, ?)", (url, title))
        self.conn.commit()
    def get_bookmarks(self):
        self.cursor.execute("SELECT title, url FROM bookmarks ORDER BY title ASC")
        return self.cursor.fetchall()
    def clear_bookmarks(self):
        self.cursor.execute("DELETE FROM bookmarks"); self.conn.commit()
    def delete_bookmark(self, url):
        self.cursor.execute("DELETE FROM bookmarks WHERE url = ?", (url,))
        self.conn.commit()

class CustomWebEnginePage(QWebEnginePage):
    def __init__(self, profile, main_window, parent=None):
        super().__init__(profile, parent)
        self.main_window = main_window
        self.featurePermissionRequested.connect(self.onFeaturePermissionRequested)
    def createWindow(self, _type): return self.main_window.add_new_tab(label="Pop-up")
    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        menu.addSeparator()
        inspect_action = menu.addAction("Element untersuchen")
        action = menu.exec_(event.globalPos())
        if action == inspect_action: self.triggerAction(QWebEnginePage.InspectElement)
    def onFeaturePermissionRequested(self, url, feature): self.setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if url.scheme() not in ('http', 'https', 'ftp', 'file', 'about'):
            webbrowser.open(url.toString())
            return False
        return super().acceptNavigationRequest(url, _type, isMainFrame)

class SettingsDialog(QDialog):
    def __init__(self, config, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager; self.main_window = parent; self.config = config
        self.setWindowTitle("Settings"); self.setMinimumWidth(450)
        layout = QVBoxLayout(self); form_layout = QFormLayout()
        self.homepage_edit = QLineEdit(self.config.get('settings', 'homepage', fallback='https://www.google.com'))
        form_layout.addRow(QLabel("Homepage:"), self.homepage_edit)
        self.force_https_check = QCheckBox("Always force HTTPS"); self.force_https_check.setChecked(self.config.getboolean('settings', 'force_https', fallback=True))
        form_layout.addRow(self.force_https_check)
        self.restore_session_check = QCheckBox("Restore previous session on startup"); self.restore_session_check.setChecked(self.config.getboolean('tabs', 'restore_session', fallback=False))
        form_layout.addRow(QLabel("<b>Tabs:</b>"), self.restore_session_check)
        self.cookie_policy_combo = QComboBox(); self.cookie_policy_combo.addItems(["Allow all cookies", "Block all cookies", "Delete cookies on exit"]); self.cookie_policy_combo.setCurrentIndex(self.config.getint('privacy', 'cookie_policy', fallback=0))
        form_layout.addRow(QLabel("<b>Privacy:</b>"), self.cookie_policy_combo)
        self.clear_history_button = QPushButton("Clear History Now"); self.clear_history_button.clicked.connect(self.clear_history)
        self.clear_bookmarks_button = QPushButton("Clear Bookmarks Now"); self.clear_bookmarks_button.clicked.connect(self.clear_bookmarks)
        form_layout.addRow("", self.clear_history_button); form_layout.addRow("", self.clear_bookmarks_button)
        self.cache_check = QCheckBox("Enable persistent disk cache (faster loading)"); self.cache_check.setChecked(self.config.getboolean('performance', 'persistent_cache', fallback=False))
        form_layout.addRow(QLabel("<b>Performance:</b>"), self.cache_check)
        self.clear_cache_button = QPushButton("Clear Cache Now"); self.clear_cache_button.clicked.connect(self.clear_cache)
        form_layout.addRow("", self.clear_cache_button)
        restart_note = QLabel("<i>Some changes (like cache) require a restart to take effect.</i>"); restart_note.setStyleSheet("color: #aaa;")
        form_layout.addRow("", restart_note)
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); button_box.accepted.connect(self.accept); button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    def clear_cache(self): self.main_window.clear_cache(); self.clear_cache_button.setText("Cache Cleared!"); self.clear_cache_button.setEnabled(False)
    def clear_history(self): self.db_manager.clear_history(); self.clear_history_button.setText("History Cleared!"); self.clear_history_button.setEnabled(False)
    def clear_bookmarks(self): self.db_manager.clear_bookmarks(); self.clear_bookmarks_button.setText("Bookmarks Cleared!"); self.clear_bookmarks_button.setEnabled(False)
    def accept(self):
        self.config.set('settings', 'homepage', self.homepage_edit.text()); self.config.set('settings', 'force_https', str(self.force_https_check.isChecked()))
        if not self.config.has_section('tabs'): self.config.add_section('tabs'); self.config.set('tabs', 'restore_session', str(self.restore_session_check.isChecked()))
        if not self.config.has_section('privacy'): self.config.add_section('privacy'); self.config.set('privacy', 'cookie_policy', str(self.cookie_policy_combo.currentIndex()))
        if not self.config.has_section('performance'): self.config.add_section('performance'); self.config.set('performance', 'persistent_cache', str(self.cache_check.isChecked()))
        super().accept()

class HistoryDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent); self.main_window = parent; self.setWindowTitle("History"); self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self); self.list_widget = QListWidget()
        for title, url in db_manager.get_history():
            item = QListWidgetItem(f"{title}\n{url}"); item.setData(Qt.UserRole, url); self.list_widget.addItem(item)
        self.list_widget.itemClicked.connect(self.item_clicked); layout.addWidget(self.list_widget)
    def item_clicked(self, item): url = item.data(Qt.UserRole); self.main_window.add_new_tab(QUrl(url), "History"); self.close()

class BookmarksDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager; self.main_window = parent
        self.setWindowTitle("Manage Bookmarks"); self.setMinimumSize(600, 400)
        layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.update_list()
        self.list_widget.itemClicked.connect(self.item_clicked)
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_bookmark)
        button_layout.addWidget(self.delete_button)
        layout.addLayout(button_layout)

    def update_list(self):
        self.list_widget.clear()
        for title, url in self.db.get_bookmarks():
            item = QListWidgetItem(f"{title}\n{url}"); item.setData(Qt.UserRole, url); self.list_widget.addItem(item)
    def item_clicked(self, item):
        url = item.data(Qt.UserRole); self.main_window.add_new_tab(QUrl(url), "Bookmark"); self.close()
    def delete_bookmark(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            url = current_item.data(Qt.UserRole); self.db.delete_bookmark(url); self.update_list()

class DownloadItemWidget(QWidget):
    def __init__(self, download_item: QWebEngineDownloadItem, parent=None):
        super().__init__(parent)
        self.item = download_item
        layout = QHBoxLayout(self)
        self.label = QLabel(os.path.basename(download_item.path()))
        self.progress = QProgressBar()
        layout.addWidget(self.label); layout.addWidget(self.progress)
        download_item.downloadProgress.connect(self.update_progress)
        download_item.finished.connect(self.on_finished)
    def update_progress(self, received, total):
        if total > 0: self.progress.setValue(int(100 * received / total))
    def on_finished(self):
        self.label.setText(f"{self.label.text()} (Completed)")
        self.progress.hide()

class DownloadsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Downloads"); self.setMinimumSize(500, 300)
        self.layout = QVBoxLayout(self)
    def add_download(self, download_item):
        item_widget = DownloadItemWidget(download_item)
        self.layout.addWidget(item_widget)

class SecureBrowser(QMainWindow):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager; self.config = configparser.ConfigParser(); self.config.read('config.ini')
        use_cache = self.config.getboolean('performance', 'persistent_cache', fallback=False)
        profile_name = "TiwutPersistentProfile" if use_cache else "TiwutVolatileProfile"
        self.profile = QWebEngineProfile(profile_name, self)
        if use_cache:
            cache_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "cache")
            self.profile.setCachePath(cache_path); self.profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        else:
            self.profile.setHttpCacheType(QWebEngineProfile.MemoryHttpCache)
        self.apply_cookie_policy()
        
        self.downloads_dialog = DownloadsDialog(self)
        self.profile.downloadRequested.connect(self.on_download_requested)
        
        self.setWindowTitle("Tiwut Secure Browser"); self.setMinimumSize(1024, 768)
        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab); self.tabs.currentChanged.connect(self.tab_changed)
        self.setCentralWidget(self.tabs)
        self.icons_dir = os.path.dirname(os.path.realpath(__file__))
        nav_bar = QToolBar("Navigation"); nav_bar.setMovable(False); nav_bar.setIconSize(QSize(22, 22)); self.addToolBar(nav_bar)
        
        self.back_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'back.png')), "")
        self.forward_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'forward.png')), "")
        self.reload_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'reload.png')), "")
        self.home_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'home.png')), "")
        self.add_bookmark_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'star.png')), "")
        self.manage_bookmarks_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'bookmark.png')), "")
        self.history_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'history.png')), "")
        self.downloads_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'download.png')), "")
        self.add_tab_btn = QPushButton("+")
        self.settings_btn = QPushButton(QIcon(os.path.join(self.icons_dir, 'icons', 'settings.png')), "")
        
        self.url_bar = QLineEdit()
        nav_bar.addWidget(self.back_btn); nav_bar.addWidget(self.forward_btn); nav_bar.addWidget(self.reload_btn); nav_bar.addWidget(self.home_btn)
        nav_bar.addWidget(self.url_bar)
        nav_bar.addWidget(self.add_bookmark_btn)
        nav_bar.addWidget(self.manage_bookmarks_btn); nav_bar.addWidget(self.history_btn); nav_bar.addWidget(self.downloads_btn)
        nav_bar.addWidget(self.add_tab_btn); nav_bar.addWidget(self.settings_btn)

        self.back_btn.clicked.connect(lambda: self.active_browser() and self.active_browser().back())
        self.forward_btn.clicked.connect(lambda: self.active_browser() and self.active_browser().forward())
        self.reload_btn.clicked.connect(lambda: self.active_browser() and self.active_browser().reload())
        self.home_btn.clicked.connect(self.navigate_home)
        self.add_bookmark_btn.clicked.connect(self.add_bookmark)
        self.manage_bookmarks_btn.clicked.connect(self.show_bookmarks)
        self.history_btn.clicked.connect(self.show_history)
        self.downloads_btn.clicked.connect(self.downloads_dialog.show)
        self.settings_btn.clicked.connect(self.open_settings)
        self.add_tab_btn.clicked.connect(lambda: self.add_new_tab())
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        
        self.status_bar = QStatusBar(); self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar(); self.progress_bar.setMaximumWidth(200); self.progress_bar.setTextVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        if not self.restore_session():
            self.add_new_tab(QUrl(self.config.get('settings', 'homepage', fallback='https://www.google.com')), "Startseite")
        self.showMaximized()

    def on_download_requested(self, download: QWebEngineDownloadItem):
        path, _ = QFileDialog.getSaveFileName(self, "Save File", download.path())
        if path:
            download.setPath(path)
            download.accept()
            self.downloads_dialog.add_download(download)
            self.downloads_dialog.show()

    def add_bookmark(self):
        if not self.active_browser(): return
        url = self.active_browser().url().toString(); title = self.active_browser().title()
        if url and title and "about:blank" not in url:
            self.db.add_bookmark(url, title); self.statusBar().showMessage("Bookmark added!", 2000)

    def show_bookmarks(self):
        dialog = BookmarksDialog(self.db, self); dialog.exec_()
        
    def show_history(self):
        dialog = HistoryDialog(self.db, self); dialog.exec_()

    def add_new_tab(self, qurl=None, label="Neuer Tab"):
        browser = QWebEngineView(); page = CustomWebEnginePage(self.profile, self, browser); browser.setPage(page)
        if qurl is None: qurl = QUrl(self.config.get('settings', 'homepage', fallback='https://www.google.com'))
        browser.setUrl(qurl); i = self.tabs.addTab(browser, label); self.tabs.setCurrentIndex(i)
        browser.urlChanged.connect(lambda q, b=browser: self.update_url_bar(q, b))
        browser.loadProgress.connect(lambda p, b=browser: self.update_progress_bar(p, b))
        browser.titleChanged.connect(lambda t, b=browser: self.update_tab_title(t, b))
        browser.loadFinished.connect(lambda _, b=browser: self.on_load_finished(b)); return page
    def on_load_finished(self, browser):
        self.update_nav_buttons(browser)
        url = browser.url().toString(); title = browser.title()
        if browser == self.active_browser() and title and url and "about:blank" not in url: self.db.add_history_entry(url, title)
    def open_settings(self):
        dialog = SettingsDialog(self.config, self.db, self)
        if dialog.exec_() == QDialog.Accepted:
            with open('config.ini', 'w') as configfile: self.config.write(configfile)
            self.statusBar().showMessage("Settings saved. Some changes require a restart.", 3000)
            self.apply_cookie_policy()
    def clear_cache(self): self.profile.clearHttpCache(); self.statusBar().showMessage("Cache has been cleared.", 2000)
    def apply_cookie_policy(self):
        policy = self.config.getint('privacy', 'cookie_policy', fallback=0)
        cookie_store = self.profile.cookieStore()
        if policy == 1: cookie_store.setCookieFilter(lambda request: False)
        else: cookie_store.setCookieFilter(lambda request: True)
    def closeEvent(self, event):
        if self.config.getboolean('tabs', 'restore_session', fallback=False):
            urls = [self.tabs.widget(i).url().toString() for i in range(self.tabs.count())]
            if not self.config.has_section('session'): self.config.add_section('session')
            self.config.set('session', 'open_tabs', ','.join(urls))
        else:
            if self.config.has_option('session', 'open_tabs'): self.config.set('session', 'open_tabs', '')
        if self.config.getint('privacy', 'cookie_policy', fallback=0) == 2: self.profile.cookieStore().deleteAllCookies()
        with open('config.ini', 'w') as configfile: self.config.write(configfile)
        event.accept()
    def restore_session(self):
        if self.config.getboolean('tabs', 'restore_session', fallback=False):
            urls = self.config.get('session', 'open_tabs', fallback='').split(',')
            urls = [url for url in urls if url]
            if urls:
                for url in urls: self.add_new_tab(QUrl(url), "Laden..."); return True
        return False
    def close_tab(self, i):
        if self.tabs.count() < 2: self.close()
        else: self.tabs.removeTab(i)
    def tab_changed(self, i):
        if i > -1 and self.active_browser():
            self.update_url_bar(self.active_browser().url()); self.update_nav_buttons(self.active_browser())
    def active_browser(self): return self.tabs.currentWidget()
    def navigate_home(self):
        if self.active_browser(): self.active_browser().setUrl(QUrl(self.config.get('settings', 'homepage', fallback='https://www.google.com')))
    def navigate_to_url(self):
        if not self.active_browser(): return
        url_text = self.url_bar.text().strip()
        force_https = self.config.getboolean('settings', 'force_https', fallback=True)
        if ' ' in url_text or '.' not in url_text: url = QUrl(f"https://www.google.com/search?q={url_text.replace(' ', '+')}")
        else:
            if force_https and url_text.startswith("http://"): url_text = url_text.replace("http://", "https://", 1)
            if not (url_text.startswith("https://") or url_text.startswith("http://")): url_text = "https://" + url_text
            url = QUrl(url_text)
        self.active_browser().setUrl(url)
    def update_url_bar(self, q, browser=None):
        if browser is None or browser == self.active_browser():
            self.url_bar.setText(q.toString()); self.url_bar.setCursorPosition(0)
    def update_tab_title(self, title, browser):
        idx = self.tabs.indexOf(browser)
        if idx != -1: self.tabs.setTabText(idx, title[:20])
        if browser == self.active_browser(): self.setWindowTitle(f"{title} - Tiwut Secure Browser")
    def update_progress_bar(self, progress, browser):
        if browser == self.active_browser():
            if 0 < progress < 100: self.progress_bar.setValue(progress); self.progress_bar.show()
            else: self.progress_bar.hide()
    def update_nav_buttons(self, browser):
        if browser == self.active_browser():
            history = browser.history()
            self.back_btn.setEnabled(history.canGoBack()); self.forward_btn.setEnabled(history.canGoForward())

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    app.setStyleSheet(FINAL_DARK_STYLE)
    
    db_manager = DatabaseManager()
    window = SecureBrowser(db_manager)
    sys.exit(app.exec_())
