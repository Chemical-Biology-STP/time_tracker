"""
Main application window with system tray integration.
"""

import sys
from PySide6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu, QMessageBox
)
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QTimer

from api_client import APIClient
from settings_manager import SettingsManager
from prompt_dialog import PromptDialog
from settings_dialog import SettingsDialog


class TimeTrackerApp:
    """Main application class with system tray integration."""
    
    def __init__(self):
        self.settings_manager = SettingsManager()
        self.api_client = APIClient(self.settings_manager.backend_url)
        
        self.tray_icon = None
        self.prompt_timer = None
        self.prompt_dialog = None
        self.settings_dialog = None
        
        self.setup_tray()
        self.setup_timer()
    
    def setup_tray(self):
        """Set up the system tray icon and menu."""
        self.tray_icon = QSystemTrayIcon()
        
        # Use a built-in icon or create one
        icon = QIcon.fromTheme("clock", QIcon())
        if icon.isNull():
            # Fallback: create a simple colored icon
            from PyQt6.QtGui import QPixmap, QPainter, QColor
            pixmap = QPixmap(32, 32)
            pixmap.fill(QColor(0, 120, 212))
            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(painter.font())
            painter.drawText(pixmap.rect(), 0x84, "T")  # Qt.AlignCenter
            painter.end()
            icon = QIcon(pixmap)
        
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("Time Tracker Companion")
        
        # Create context menu
        menu = QMenu()
        
        # Log Time action
        log_action = QAction("Log Time...", menu)
        log_action.triggered.connect(self.show_prompt)
        menu.addAction(log_action)
        
        menu.addSeparator()
        
        # Open Web Interface
        web_action = QAction("Open Web Interface", menu)
        web_action.triggered.connect(self.open_web_interface)
        menu.addAction(web_action)
        
        menu.addSeparator()
        
        # Settings action
        settings_action = QAction("Settings...", menu)
        settings_action.triggered.connect(self.show_settings)
        menu.addAction(settings_action)
        
        menu.addSeparator()
        
        # Connection status
        self.status_action = QAction("Status: Checking...", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        menu.addSeparator()
        
        # Quit action
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        
        # Double-click to show prompt
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        # Check connection status
        self.check_connection()
    
    def setup_timer(self):
        """Set up the prompt timer."""
        self.prompt_timer = QTimer()
        self.prompt_timer.timeout.connect(self.show_prompt)
        self.update_timer_interval()
    
    def update_timer_interval(self):
        """Update the timer interval from settings."""
        interval_ms = self.settings_manager.prompt_interval_minutes * 60 * 1000
        self.prompt_timer.setInterval(interval_ms)
        if not self.prompt_timer.isActive():
            self.prompt_timer.start()
    
    def show_tray_icon(self):
        """Show the system tray icon."""
        self.tray_icon.show()
    
    def on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_prompt()
    
    def show_prompt(self):
        """Show the time logging prompt dialog."""
        if self.prompt_dialog is None or not self.prompt_dialog.isVisible():
            self.prompt_dialog = PromptDialog(
                self.api_client,
                self.settings_manager
            )
            self.prompt_dialog.show()
            self.prompt_dialog.raise_()
            self.prompt_dialog.activateWindow()
    
    def show_settings(self):
        """Show the settings dialog."""
        if self.settings_dialog is None or not self.settings_dialog.isVisible():
            self.settings_dialog = SettingsDialog(
                self.api_client,
                self.settings_manager
            )
            self.settings_dialog.finished.connect(self.on_settings_closed)
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
    
    def on_settings_closed(self):
        """Handle settings dialog closed."""
        # Update timer interval in case it changed
        self.update_timer_interval()
        # Update API client URL
        self.api_client.update_base_url(self.settings_manager.backend_url)
        # Recheck connection
        self.check_connection()
    
    def open_web_interface(self):
        """Open the web interface in the default browser."""
        import webbrowser
        webbrowser.open(self.settings_manager.backend_url)
    
    def check_connection(self):
        """Check connection to the backend."""
        connected = self.api_client.health_check()
        if connected:
            self.status_action.setText("Status: Connected")
        else:
            self.status_action.setText("Status: Disconnected")
    
    def quit_app(self):
        """Quit the application."""
        self.prompt_timer.stop()
        self.tray_icon.hide()
        QApplication.quit()
