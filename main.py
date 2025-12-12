"""
ULC Finder - Main Application Entry Point
Mifare Ultralight C Authentication Key Finder

Usage:
    python main.py
"""

import sys
from PyQt5.QtWidgets import QApplication
from gui.main_window import MainWindow


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("ULC Finder")
    app.setOrganizationName("ULC Security Tools")

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run application
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
