from PySide6.QtGui import QColor, QPen
from PySide6.QtCore import Qt

DARK_STYLESHEET = """
/* Tổng thể ứng dụng */
QMainWindow, QDialog {
    background-color: #1e1e1e;
    color: #cccccc;
}

/* Dock Widgets & Toolbars */
QDockWidget {
    background-color: #252526;
    color: #cccccc;
    titlebar-close-icon: url(close.png);
    border: 1px solid #3c3c3c;
}
QDockWidget::title {
    background-color: #2d2d2d;
    padding: 6px;
    font-weight: bold;
}
QToolBar {
    background-color: #2d2d2d;
    border-bottom: 1px solid #3c3c3c;
    spacing: 5px;
    padding: 2px;
}
QToolButton {
    color: #cccccc;
    background-color: transparent;
    border-radius: 4px;
    padding: 4px;
}
QToolButton:hover {
    background-color: #3e3e42;
}

/* Menu Bar & Menus */
QMenuBar {
    background-color: #1e1e1e;
    color: #cccccc;
    border-bottom: 1px solid #2d2d2d;
}
QMenuBar::item:selected {
    background-color: #3e3e42;
}
QMenu {
    background-color: #252526;
    color: #cccccc;
    border: 1px solid #454545;
}
QMenu::item:selected {
    background-color: #04395e;
    color: #ffffff;
}

/* Các Danh sách & Bảng (Toolbox / Object Browser) */
QTreeWidget, QListWidget, QGraphicsView {
    background-color: #1e1e1e;
    color: #cccccc;
    border: 1px solid #2d2d2d;
    outline: none;
}
QTreeWidget::item:selected, QListWidget::item:selected {
    background-color: #04395e;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 4px;
    border: 1px solid #3c3c3c;
}

/* Thanh cuộn Dark Mode (Sửa triệt để thanh cuộn trắng) */
QScrollBar:vertical, QScrollBar:horizontal {
    background-color: #1e1e1e;
    width: 12px;
    height: 12px;
    margin: 0px;
}
QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
    background-color: #424242;
    min-height: 20px;
    min-width: 20px;
    border-radius: 4px;
}
QScrollBar::handle:hover {
    background-color: #4f4f4f;
}
QScrollBar::add-line, QScrollBar::sub-line {
    background: none;
    border: none;
}

/* Status Bar & Dialogs */
QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}
"""

def apply_theme(main_window, dark_mode: bool) -> None:
    """Áp dụng theme và chỉnh màu lưới Canvas dịu mắt"""
    if dark_mode:
        main_window.setStyleSheet(DARK_STYLESHEET)
        main_window.scene.setBackgroundBrush(QColor("#1e1e1e"))
        
        # Chỉnh bút vẽ lưới Canvas sang màu xám tối dịu mắt (thay vì nét đứt trắng chói)
        if hasattr(main_window, 'canvas_view'):
            main_window.canvas_view.grid_pen = QPen(QColor("#2d2d2d"), 1, Qt.PenStyle.DotLine)
            main_window.canvas_view.viewport().update()
    else:
        main_window.setStyleSheet("")
        main_window.scene.setBackgroundBrush(QColor("#ffffff"))
        
        # Trở lại lưới sáng mặc định
        if hasattr(main_window, 'canvas_view'):
            main_window.canvas_view.grid_pen = QPen(QColor("#e0e0e0"), 1, Qt.PenStyle.DotLine)
            main_window.canvas_view.viewport().update()