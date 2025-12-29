"""
gui_entry.py - GUI Entry

Launch PySide6 GUI application
"""

import sys
from pathlib import Path

# Ensure module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .gui_mainwindow import MainWindow


def main():
    """GUI main entry"""
    # High DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Batch Rename Tool")
    app.setApplicationVersion("1.0.0")

    # Set style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
