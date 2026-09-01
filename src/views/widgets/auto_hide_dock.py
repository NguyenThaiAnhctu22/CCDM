from PySide6.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
from PySide6.QtCore import Qt, QEvent, Signal
from PySide6.QtGui import QIcon

class AutoHideDock(QDockWidget):
    pinned_changed = Signal(bool) # Signal phát ra khi bấm nút ghim

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.is_pinned = True
        
        # Thay thế thanh tiêu đề mặc định bằng Custom TitleBar có nút Ghim
        self._setup_custom_title_bar(title)

    def _setup_custom_title_bar(self, title):
        title_widget = QWidget()
        layout = QHBoxLayout(title_widget)
        layout.setContentsMargins(5, 2, 5, 2)

        self.title_label = QLabel(title)
        
        # Nút Ghim (Pin / Unpin)
        self.pin_button = QPushButton("📌")
        self.pin_button.setFixedSize(20, 20)
        self.pin_button.setFlat(True)
        self.pin_button.setToolTip("Ghim / Tự động thu gọn")
        self.pin_button.clicked.connect(self.toggle_pin)

        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.pin_button)

        self.setTitleBarWidget(title_widget)

    def toggle_pin(self):
        self.is_pinned = not self.is_pinned
        self.pin_button.setText("📌" if self.is_pinned else "📍")
        self.pinned_changed.emit(self.is_pinned)