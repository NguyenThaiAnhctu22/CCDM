from PySide6.QtWidgets import QGraphicsView, QGraphicsLineItem, QGraphicsItem
from PySide6.QtCore import Qt, Signal, QLineF, QPoint, QPointF
from PySide6.QtGui import QMouseEvent, QWheelEvent, QPen, QColor, QCursor, QKeyEvent

from .items.entity_item import EntityItem
from .items.relationship_item import RelationshipItem
from ..helpers.icon_helper import create_entity_pixmap, create_relationship_pixmap


class CanvasView(QGraphicsView):

    entity_requested = Signal(float, float)
    relationship_requested = Signal(str, str)
    mode_changed = Signal(str)

    # Tăng ngưỡng dính lên 25px để dễ dàng nhận biết khi thao tác chuột
    SNAP_THRESHOLD = 50.0 

    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setRenderHints(self.renderHints())
        
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.current_mode = "POINTER"
        self._is_panning = False
        self._pan_start_pos = QPoint()
        
        self.source_entity_item = None
        self.temp_line_item = None
        self.snap_guide_line = None  # Đường gióng nét đứt trực quan khi hút căn
        self._is_dragging_rel = False

        self.shortcuts_enabled = False

    def update_all_relationships(self):
        """Cập nhật vị trí của tất cả dây nối trên Canvas"""
        if self.scene():
            for item in self.scene().items():
                if hasattr(item, 'update_position'):
                    item.update_position()
            self.scene().update()

    def set_mode(self, mode: str):
        self.source_entity_item = None
        self._is_dragging_rel = False
        self._remove_temp_line()
        self._remove_snap_guide()
        
        self.current_mode = mode

        if mode == "POINTER":
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.unsetCursor()
            self.viewport().unsetCursor()

        elif mode == "GRABBER":
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            self.viewport().setCursor(Qt.CursorShape.OpenHandCursor)

        elif mode == "ADD_ENTITY":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            pix = create_entity_pixmap(24)
            cursor = QCursor(pix, 0, 0)
            self.setCursor(cursor)
            self.viewport().setCursor(cursor)
            
        elif mode == "ADD_RELATIONSHIP":
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            pix = create_relationship_pixmap(24)
            cursor = QCursor(pix, 12, 12)
            self.setCursor(cursor)
            self.viewport().setCursor(cursor)

        self.mode_changed.emit(mode)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Bắt sự kiện phím tắt E, R, Esc khi tính năng được bật"""
        if self.shortcuts_enabled:
            # Bỏ qua nếu người dùng đang edit văn bản (như QGraphicsTextItem)
            if self.scene() and self.scene().focusItem():
                super().keyPressEvent(event)
                return

            key = event.key()
            if key == Qt.Key.Key_E:
                self.set_mode("ADD_ENTITY")
                event.accept()
                return
            elif key == Qt.Key.Key_R:
                self.set_mode("ADD_RELATIONSHIP")
                event.accept()
                return
            elif key == Qt.Key.Key_Escape:
                self.set_mode("POINTER")
                event.accept()
                return

        super().keyPressEvent(event)

    def _remove_temp_line(self):
        if self.temp_line_item and self.scene():
            self.scene().removeItem(self.temp_line_item)
            self.temp_line_item = None

    def _remove_snap_guide(self):
        """Xóa đường gióng nét đứt trực quan"""
        if self.snap_guide_line and self.scene():
            self.scene().removeItem(self.snap_guide_line)
            self.snap_guide_line = None

    def _draw_snap_guide(self, p1: QPointF, p2: QPointF):
        """Vẽ đường gióng màu đỏ nét đứt để người dùng thấy rõ trục căn thẳng"""
        if not self.snap_guide_line:
            pen = QPen(QColor("#E74C3C"), 1, Qt.PenStyle.DotLine)
            self.snap_guide_line = QGraphicsLineItem()
            self.snap_guide_line.setPen(pen)
            self.snap_guide_line.setZValue(9)
            self.scene().addItem(self.snap_guide_line)
        self.snap_guide_line.setLine(QLineF(p1, p2))

    def _start_temp_line(self, entity_item: EntityItem, scene_pos):
        self.source_entity_item = entity_item
        src_center = entity_item.sceneBoundingRect().center()

        pen = QPen(QColor("#E67E22"), 2, Qt.PenStyle.DashLine)
        self.temp_line_item = QGraphicsLineItem(QLineF(src_center, scene_pos))
        self.temp_line_item.setPen(pen)
        self.temp_line_item.setZValue(10)
       
        self.temp_line_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.temp_line_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.scene().addItem(self.temp_line_item)

    def _calculate_snapped_pos(self, src_center: QPointF, target_pos: QPointF, force_straight: bool) -> tuple[QPointF, bool]:
        """Tính toán vị trí hút căn và trả về trạng thái có dính trục hay không"""
        dx = abs(target_pos.x() - src_center.x())
        dy = abs(target_pos.y() - src_center.y())

        res_x = target_pos.x()
        res_y = target_pos.y()
        is_snapped = False

        # 1. Bắt buộc khóa trục nếu giữ phím SHIFT
        if force_straight:
            if dx > dy:
                res_y = src_center.y()
            else:
                res_x = src_center.x()
            return QPointF(res_x, res_y), True

        # 2. Hút tự động với bán kính SNAP_THRESHOLD lớn hơn (25px)
        if dx < self.SNAP_THRESHOLD:
            res_x = src_center.x()
            is_snapped = True
        if dy < self.SNAP_THRESHOLD:
            res_y = src_center.y()
            is_snapped = True

        return QPointF(res_x, res_y), is_snapped

    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self.scale(zoom_factor, zoom_factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            if self.current_mode in ["ADD_ENTITY", "ADD_RELATIONSHIP"]:
                self.set_mode("POINTER")
                event.accept()
                return

            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.position().toPoint())

        if event.button() == Qt.MouseButton.LeftButton and self.current_mode == "ADD_ENTITY":
            self.entity_requested.emit(scene_pos.x(), scene_pos.y())
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.current_mode == "ADD_RELATIONSHIP":
            clicked_item = self.scene().itemAt(scene_pos, self.transform())
            while clicked_item and not isinstance(clicked_item, EntityItem):
                clicked_item = clicked_item.parentItem()

            if isinstance(clicked_item, EntityItem):
                if not self.source_entity_item:
                    # Lần click 1: Chọn Entity nguồn
                    self._start_temp_line(clicked_item, scene_pos)
                    self._is_dragging_rel = True
                else:
                    # Lần click 2: Chọn Entity đích (Chế độ Click-Click)
                    src_id = self.source_entity_item.entity.id
                    tgt_id = clicked_item.entity.id
                    
                    self._remove_temp_line()
                    self._remove_snap_guide()
                    
                    self.relationship_requested.emit(src_id, tgt_id)
                    self.update_all_relationships()
                    
                    self.source_entity_item = None
                    self._is_dragging_rel = False

            event.accept()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self._is_panning = True
            self._pan_start_pos = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.position().toPoint() - self._pan_start_pos
            self._pan_start_pos = event.position().toPoint()

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return

        if self.current_mode == "ADD_RELATIONSHIP" and self._is_dragging_rel and self.source_entity_item and self.temp_line_item:
            raw_scene_pos = self.mapToScene(event.position().toPoint())
            src_center = self.source_entity_item.sceneBoundingRect().center()
            
            is_shift_pressed = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
            snapped_pos, is_snapped = self._calculate_snapped_pos(src_center, raw_scene_pos, is_shift_pressed)
            
            self.temp_line_item.setLine(QLineF(src_center, snapped_pos))

            # Hiển thị đường gióng đỏ khi có sự kiện hút căn thẳng
            if is_snapped:
                self._draw_snap_guide(src_center, snapped_pos)
            else:
                self._remove_snap_guide()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if (event.button() == Qt.MouseButton.RightButton or event.button() == Qt.MouseButton.MiddleButton) and self._is_panning:
            self._is_panning = False
            self.set_mode(self.current_mode)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.current_mode == "ADD_RELATIONSHIP" and self._is_dragging_rel:
            scene_pos = self.mapToScene(event.position().toPoint())
            
            # FIX 1: Dọn dẹp preview line (Z=10) & snap guide TRƯỚC khi thực hiện itemAt()
            # Giúp itemAt() không bị bắt trúng đầu mút của temp_line_item (đặc biệt khi nối xéo)
            self._remove_temp_line()
            self._remove_snap_guide()

            released_item = self.scene().itemAt(scene_pos, self.transform())
            while released_item and not isinstance(released_item, EntityItem):
                released_item = released_item.parentItem()

            if isinstance(released_item, EntityItem):
                # Chỉ thực hiện snap căn lề nếu nối giữa 2 Entity khác nhau
                if released_item != self.source_entity_item:
                    src_center = self.source_entity_item.sceneBoundingRect().center()
                    tgt_center = released_item.sceneBoundingRect().center()

                    dx = abs(src_center.x() - tgt_center.x())
                    dy = abs(src_center.y() - tgt_center.y())
                    is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)

                    if is_shift or dx < self.SNAP_THRESHOLD or dy < self.SNAP_THRESHOLD:
                        if dx < dy:
                            new_x = src_center.x() - released_item.rect().width() / 2
                            released_item.setPos(new_x, released_item.pos().y())
                            released_item.entity.x = new_x
                        else:
                            new_y = src_center.y() - released_item.rect().height() / 2
                            released_item.setPos(released_item.pos().x(), new_y)
                            released_item.entity.y = new_y

                src_id = self.source_entity_item.entity.id
                tgt_id = released_item.entity.id
                
                # Phát signal yêu cầu tạo Relationship (src_id và tgt_id bằng nhau khi là Self-Relationship)
                self.relationship_requested.emit(src_id, tgt_id)
                self.update_all_relationships()

            # FIX 2: Reset biến trạng thái ra bên ngoài để tránh bị kẹt trạng thái "đang kéo" khi thả chuột hụt ra ngoài
            self.source_entity_item = None
            self._is_dragging_rel = False

            event.accept()
            return

        super().mouseReleaseEvent(event)