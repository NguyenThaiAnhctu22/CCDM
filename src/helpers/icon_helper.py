from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QBrush, QCursor
from PySide6.QtCore import Qt, QRectF, QPointF

def create_entity_pixmap(size=24) -> QPixmap:
    """Vẽ icon hình chữ nhật đại diện cho Entity"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent) # Nền trong suốt

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Vẽ khung Entity (Hình chữ nhật viền xanh, nền trắng)
    painter.setPen(QPen(QColor("#0055ff"), 2))
    painter.setBrush(QBrush(QColor("#e6f0ff")))
    painter.drawRoundedRect(2, 4, size - 4, size - 8, 3, 3)

    # Vẽ 2 dải dòng tượng trưng cho thuộc tính bên trong
    painter.setPen(QPen(QColor("#00afef"), 1.5))
    painter.drawLine(6, 10, size - 6, 10)
    painter.drawLine(6, 15, size - 10, 15)

    painter.end()
    return pixmap


def create_relationship_pixmap(size=24) -> QPixmap:
    """Vẽ icon đường dây nối 2 điểm đại diện cho Quan hệ"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Vẽ đường dây zigzag/đường nối
    painter.setPen(QPen(QColor("#1f5ca9"), 2))
    painter.drawLine(4, size - 4, 10, size - 4)
    painter.drawLine(10, size - 4, 10, 4)
    painter.drawLine(10, 4, size - 4, 4)

    # Vẽ 2 điểm tròn ghim ở 2 đầu dây
    painter.setBrush(QBrush(QColor("#1f5ca9")))
    painter.drawEllipse(QPointF(4, size - 4), 3, 3)
    painter.drawEllipse(QPointF(size - 4, 4), 3, 3)

    painter.end()
    return pixmap