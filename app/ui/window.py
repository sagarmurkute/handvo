"""Main application window for HANDVO hand tracking interface."""

from PySide6.QtWidgets import QMainWindow
from app.ui.main_window import MainWindow

# Provide alias window class matching modular layout
class HandvoWindow(MainWindow):
    """Main window alias for HANDVO interface."""
    pass
