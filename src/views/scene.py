from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import Qt
from PySide6.QtGui import QPen, QColor

class DiagramScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self.grid_size = 20
        self.grid_color = QColor("#E0E0E0")

    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        # Vẽ lưới tọa độ (Grid background)
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        lines = []
        for x in range(left, int(rect.right()), self.grid_size):
            lines.append(((x, rect.top()), (x, rect.bottom())))
        for y in range(top, int(rect.bottom()), self.grid_size):
            lines.append(((rect.left(), y), (rect.right(), y)))

        painter.setPen(QPen(self.grid_color, 1, Qt.PenStyle.DotLine))
        for line in lines:
            painter.drawLine(line[0][0], line[0][1], line[1][0], line[1][1])