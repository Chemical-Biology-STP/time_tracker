#!/usr/bin/env python3
"""
Time Tracker Companion - Windows Edition
A system tray application for logging time entries to the Flask backend.
"""

import sys
import os

# Add parent directory to path for imports when running from source
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app_window import TimeTrackerApp


def main():
    """Main entry point for the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
    app.setApplicationName("Time Tracker Companion")
    app.setOrganizationName("TimeTracker")
    
    # Create and show the main application
    window = TimeTrackerApp()
    window.show_tray_icon()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
