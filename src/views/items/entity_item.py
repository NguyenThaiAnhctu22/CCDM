import math
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QGraphicsItem
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QFont, QFontMetrics
from ...models.entity import Entity
from ..dialogs.entity_dialog import EntityDialog


class ResizeHandleItem(QGraphicsRectItem):
    """Nốt nhỏ hỗ trợ kéo kích thước khi Entity được chọn (Góc và Trung điểm cạnh)"""
    HANDLE_SIZE = 8
    
    # Định nghĩa các loại handle
    TYPE_TOP_LEFT = "top_left"
    TYPE_TOP_RIGHT = "top_right"
    TYPE_BOTTOM_LEFT = "bottom_left"
    TYPE_BOTTOM_RIGHT = "bottom_right"
    TYPE_TOP = "top"
    TYPE_BOTTOM = "bottom"
    TYPE_LEFT = "left"
    TYPE_RIGHT = "right"

    def __init__(self, handle_type: str, parent_entity):
        # Vẽ nút nằm giữa điểm neo
        s = ResizeHandleItem.HANDLE_SIZE
        super().__init__(-s/2, -s/2, s, s, parent_entity)
        self.handle_type = handle_type
        self.parent_entity = parent_entity
        
        # Style mặc định cho nút góc
        self.setBrush(QBrush(QColor("#FFFFFF")))
        self.setPen(QPen(QColor("#E74C3C"), 1.5)) # Màu đỏ
        
        # Đặt Cursor phù hợp
        self._set_cursor()

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

    def _set_cursor(self):
        t = self.handle_type
        if t in [self.TYPE_TOP_LEFT, self.TYPE_BOTTOM_RIGHT]:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif t in [self.TYPE_TOP_RIGHT, self.TYPE_BOTTOM_LEFT]:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif t in [self.TYPE_TOP, self.TYPE_BOTTOM]:
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif t in [self.TYPE_LEFT, self.TYPE_RIGHT]:
            self.setCursor(Qt.CursorShape.SizeHorCursor)

    def mousePressEvent(self, event):
        # Khi đang kéo nút, không cho phép di chuyển cả Entity
        self.parent_entity.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        # Lưu lại vị trí chuột và hình chữ nhật ban đầu để tính toán delta
        self._drag_start_pos = event.scenePos()
        self._initial_rect = self.parent_entity.rect()
        self._initial_entity_pos = self.parent_entity.pos()
        event.accept()

    def mouseMoveEvent(self, event):
        # Tính toán độ chênh lệch di chuyển của chuột trong Scene
        delta = event.scenePos() - self._drag_start_pos
        dx = delta.x()
        dy = delta.y()

        current_rect = QRectF(self._initial_rect)
        new_pos = QPointF(self._initial_entity_pos)
        
        t = self.handle_type
        
        # 1. TÍNH KÍCH THƯỚC TỐI THIỂU ĐỘNG (Dựa trên cả width và height của nội dung)
        min_w = self.parent_entity.calculate_auto_width()
        min_h = self.parent_entity.calculate_auto_height()

        # --- Logic thay đổi kích thước và vị trí phức tạp ---
        # 1. Xử lý chiều ngang (Width và X)
        if t in [self.TYPE_LEFT, self.TYPE_TOP_LEFT, self.TYPE_BOTTOM_LEFT]:
            # Kéo cạnh trái: Thay đổi cả X và Width. Cạnh phải ghim cố định.
            max_dx = self._initial_rect.width() - min_w
            actual_dx = min(dx, max_dx) # dx dương -> thu hẹp, dx âm -> giãn ra
            
            new_pos.setX(self._initial_entity_pos.x() + actual_dx)
            current_rect.setWidth(self._initial_rect.width() - actual_dx)
            
        elif t in [self.TYPE_RIGHT, self.TYPE_TOP_RIGHT, self.TYPE_BOTTOM_RIGHT]:
            # Kéo cạnh phải: Chỉ thay đổi Width. Cạnh trái ghim cố định.
            new_width = max(min_w, self._initial_rect.width() + dx)
            current_rect.setWidth(new_width)

        # 2. Xử lý chiều dọc (Height và Y)
        if t in [self.TYPE_TOP, self.TYPE_TOP_LEFT, self.TYPE_TOP_RIGHT]:
            # Kéo cạnh trên: Thay đổi cả Y và Height. Cạnh dưới ghim cố định.
            max_dy = self._initial_rect.height() - min_h
            actual_dy = min(dy, max_dy)
            
            new_pos.setY(self._initial_entity_pos.y() + actual_dy)
            current_rect.setHeight(self._initial_rect.height() - actual_dy)
            
        elif t in [self.TYPE_BOTTOM, self.TYPE_BOTTOM_LEFT, self.TYPE_BOTTOM_RIGHT]:
            # Kéo cạnh dưới: Chỉ thay đổi Height. Cạnh trên ghim cố định.
            new_height = max(min_h, self._initial_rect.height() + dy)
            current_rect.setHeight(new_height)

        # --- Áp dụng thay đổi ---
        # Chuẩn bị thay đổi hình học
        self.parent_entity.prepareGeometryChange()
        
        # Cập nhật vị trí Entity trong Scene (quan trọng khi kéo cạnh trên/trái)
        self.parent_entity.setPos(new_pos)
        
        # Cập nhật hình chữ nhật (kích thước) và lưu vào Model
        self.parent_entity.manual_resize(current_rect.width(), current_rect.height())
        
        event.accept()

    def mouseReleaseEvent(self, event):
        # Trả lại quyền di chuyển cho Entity
        self.parent_entity.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        if hasattr(self, '_drag_start_pos'):
            del self._drag_start_pos
            del self._initial_rect
            del self._initial_entity_pos
        event.accept()

class PKTextItem(QGraphicsTextItem):
    """QGraphicsTextItem tùy chỉnh tự vẽ gạch chân sát viền chữ, khớp hoàn hảo với dấu _"""

    # Độ dày mặc định của đường gạch chân khóa chính (px). Tăng số này để gạch chân đậm/dày hơn.
    UNDERLINE_WIDTH = 2.0

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)

    def paint(self, painter, option, widget=None):
        # 1. Vẽ chữ bình thường (không dùng QFont.setUnderline)
        super().paint(painter, option, widget)

        # 2. Vẽ đường gạch chân custom
        fm = QFontMetrics(self.font())
        text_str = self.toPlainText()
        text_width = fm.horizontalAdvance(text_str)
        
        # Lấy độ cao baseline chân chữ (trừ bớt padding margins mặc định của QGraphicsTextItem)
        ascent = fm.ascent()
        margin = 4.45  # Document margin mặc định của QGraphicsTextItem là 4px
        
        # Đặt y_line sát chân chữ (ngang bằng vị trí gạch dưới _)
        y_line = margin + ascent + 2.0

        pen = QPen(self.defaultTextColor(), self.UNDERLINE_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(margin, y_line), QPointF(margin + text_width, y_line))

class EntityItem(QGraphicsRectItem):
    GRID_SIZE = 15
    simplified_mode: bool = False

    def __init__(self, entity: Entity, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.relations = []

        # Font & Màu sắc chuẩn PowerDesigner
        self.entity_font = QFont("Readdex Pro", 13)
        self.entity_color = QColor("#000000")
        self.attribute_font = QFont("Readdex Pro", 13)
        self.attribute_color = QColor("#000000")
        
        # SỬA LỖI: Dùng chuẩn QGraphicsItem.GraphicsItemFlag
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges
        )
        
        # Kích thước khung
        self.header_height = 32
        self.line_height = 26  # Tăng nhẹ độ cao dòng cho vừa cỡ chữ 10
        self.min_width = 140
        self.custom_width = None
        self.custom_height = None

        # Viền xanh ngọc Cyan đậm hơn (tăng tương phản, giống PowerDesigner)
        self.border_pen = QPen(QColor("#1f5ca9"), 1.8)
        self.setPen(self.border_pen)
        
        # Tiêu đề Entity
        self.title_item = QGraphicsTextItem(self)
        self.title_item.setFont(self.entity_font)
        self.title_item.setDefaultTextColor(self.entity_color)
        
        self.attr_items = []

        # --- KHỞI TẠO 8 NỐT THU PHÓNG ---
        h_types = ResizeHandleItem
        self.handles = {
            # 4 Góc
            h_types.TYPE_TOP_LEFT: ResizeHandleItem(h_types.TYPE_TOP_LEFT, self),
            h_types.TYPE_TOP_RIGHT: ResizeHandleItem(h_types.TYPE_TOP_RIGHT, self),
            h_types.TYPE_BOTTOM_LEFT: ResizeHandleItem(h_types.TYPE_BOTTOM_LEFT, self),
            h_types.TYPE_BOTTOM_RIGHT: ResizeHandleItem(h_types.TYPE_BOTTOM_RIGHT, self),
            # 4 Cạnh (Mới)
            h_types.TYPE_TOP: ResizeHandleItem(h_types.TYPE_TOP, self),
            h_types.TYPE_BOTTOM: ResizeHandleItem(h_types.TYPE_BOTTOM, self),
            h_types.TYPE_LEFT: ResizeHandleItem(h_types.TYPE_LEFT, self),
            h_types.TYPE_RIGHT: ResizeHandleItem(h_types.TYPE_RIGHT, self),
        }
        
        # Tùy chỉnh màu sắc khác cho nút cạnh (ví dụ: viền xanh dương)
        side_pen = QPen(QColor("#3498DB"), 1.2)
        for h_type in [h_types.TYPE_TOP, h_types.TYPE_BOTTOM, h_types.TYPE_LEFT, h_types.TYPE_RIGHT]:
            self.handles[h_type].setPen(side_pen)

        self._set_handles_visible(False)
        
        self.update_content()
        self.setPos(self.entity.x, self.entity.y)
        self.setZValue(2)

    def _set_handles_visible(self, visible: bool):
        for handle in self.handles.values():
            handle.setVisible(visible)

    def calculate_auto_width(self) -> float:
        fm_title = QFontMetrics(self.entity_font)
        max_w = fm_title.horizontalAdvance(self.entity.name) + 30

        fm_attr = QFontMetrics(self.attribute_font)
        for attr in self.entity.attributes:
            if EntityItem.simplified_mode:
                text = f"  {attr.name}"
            else:
                text = f"{attr.name} : {attr.data_type}"
            
            w = fm_attr.horizontalAdvance(text) + 20
            if w > max_w:
                max_w = w

        return max(self.min_width, max_w)

    def calculate_auto_height(self) -> float:
        """Hàm mới: Tính toán chiều cao tối thiểu cần thiết dựa trên danh sách attributes"""
        total_attrs_count = len(self.entity.attributes)
        attrs_section_h = max(24, total_attrs_count * self.line_height + 6)
        return self.header_height + attrs_section_h

    def update_content(self):
        self.prepareGeometryChange()

        self.title_item.setPlainText(self.entity.name)
        self.title_item.setFont(self.entity_font)
        self.title_item.setDefaultTextColor(self.entity_color)

        # Tính chiều rộng (Ưu tiên lấy từ Model)
        auto_w = self.calculate_auto_width()
        custom_w = getattr(self.entity, 'custom_width', None) or self.custom_width
        width = max(custom_w, auto_w) if custom_w else auto_w

        auto_h = self.calculate_auto_height()
        custom_h = getattr(self.entity, 'custom_height', None) or self.custom_height
        height = max(custom_h, auto_h) if custom_h else auto_h

        # Tách thuộc tính thành 2 nhóm: PK và Thuộc tính thường
        pk_attrs = [a for a in self.entity.attributes if a.is_pk]
        non_pk_attrs = [a for a in self.entity.attributes if not a.is_pk]

        self.setRect(0, 0, width, height)

        # Căn giữa Tiêu đề Entity
        title_width = self.title_item.boundingRect().width()
        self.title_item.setPos((width - title_width) / 2, 2)

        # Vẽ lại thuộc tính
        for item in self.attr_items:
            if item.scene():
                item.scene().removeItem(item)
        self.attr_items.clear()

        # Ngăn 2: PK Attributes
        y_offset = self.header_height + 3
        for attr in pk_attrs:
            attr_f = QFont(self.attribute_font)
            
            if EntityItem.simplified_mode or not attr.data_type:
                text = attr.name
            else:
                text = f"{attr.name} : {attr.data_type}"

            attr_item = PKTextItem(text, self)
            attr_item.setFont(attr_f)
            attr_item.setDefaultTextColor(self.attribute_color)
            attr_item.setPos(5, y_offset)
            
            self.attr_items.append(attr_item)
            y_offset += self.line_height

        # Ngăn 3: Non-PK Attributes
        for attr in non_pk_attrs:
            attr_f = QFont(self.attribute_font)

            if EntityItem.simplified_mode or not attr.data_type:
                text = attr.name
            else:
                text = f"{attr.name} : {attr.data_type}"
            
            attr_item = QGraphicsTextItem(text, self)
            attr_item.setFont(attr_f)
            attr_item.setDefaultTextColor(self.attribute_color)
            attr_item.setPos(5, y_offset)
            
            self.attr_items.append(attr_item)
            y_offset += self.line_height

        self.update_handle_positions()

    def update_handle_positions(self):
        """Cập nhật vị trí neo của 8 nút dựa trên hình chữ nhật hiện tại"""
        rect = self.rect()
        l = rect.left()
        r = rect.right()
        t = rect.top()
        b = rect.bottom()
        cx = rect.center().x()
        cy = rect.center().y()
        
        h = self.handles
        h_types = ResizeHandleItem
        
        # 4 Góc
        h[h_types.TYPE_TOP_LEFT].setPos(l, t)
        h[h_types.TYPE_TOP_RIGHT].setPos(r, t)
        h[h_types.TYPE_BOTTOM_LEFT].setPos(l, b)
        h[h_types.TYPE_BOTTOM_RIGHT].setPos(r, b)
        # 4 Cạnh (Neo vào trung điểm)
        h[h_types.TYPE_TOP].setPos(cx, t)
        h[h_types.TYPE_BOTTOM].setPos(cx, b)
        h[h_types.TYPE_LEFT].setPos(l, cy)
        h[h_types.TYPE_RIGHT].setPos(r, cy)

    def manual_resize(self, width: float, height: float):
        self.prepareGeometryChange()

        self.custom_width = width
        self.custom_height = height
        self.entity.custom_width = width
        self.entity.custom_height = height

        self.setRect(0, 0, width, height)
        
        title_w = self.title_item.boundingRect().width()
        self.title_item.setPos((width - title_w) / 2, 2)
        self.update_handle_positions()

        if hasattr(self, 'relations'):
            for rel in self.relations:
                rel.update_position()

    def paint(self, painter, option, widget=None):
        rect = self.rect()

        # 1. Vẽ nền phẳng (bỏ gradient để tránh hiệu ứng "mờ sương", giống PowerDesigner hơn)
        painter.setBrush(QBrush(QColor("#dbf7ff"))) #E6FBFB
        painter.setPen(self.border_pen)
        painter.drawRect(rect)

        # 2. Chỉ vẽ 1 đường kẻ ngang duy nhất dưới tên Entity (Phân cách Header & Body)
        line_pen = QPen(QColor("#1f5ca9"), 1.8)
        painter.setPen(line_pen)

        line1_y = rect.y() + self.header_height
        painter.drawLine(QPointF(rect.left(), line1_y), QPointF(rect.right(), line1_y))

        # 3. Khi chọn Entity -> Hiện đường viền nét đứt đỏ
        if self.isSelected():
            painter.setPen(QPen(QColor("#0080FF"), 1.5, Qt.PenStyle.DashLine)) ##E74C3C
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(rect)
            self._set_handles_visible(True)
        else:
            self._set_handles_visible(False)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if hasattr(self, 'entity'):
                self.entity.x = self.pos().x()
                self.entity.y = self.pos().y()

            # Gọi cập nhật trực tiếp cho tất cả các quan hệ đang kết nối với Entity này
            if hasattr(self, 'relations'):
                for rel in self.relations:
                    rel.update_position()

        return super().itemChange(change, value)

    def mouseDoubleClickEvent(self, event):
        # Lấy MainWindow từ View đang chứa Scene
        if self.scene() and self.scene().views():
            mw = self.scene().views()[0].window()
            # Gọi qua MainWindow để tự động lấy đúng flag auto_prefix_enabled
            if hasattr(mw, 'open_entity_dialog'):
                mw.open_entity_dialog(self)
                event.accept()
                return

        # Fallback nếu không tìm thấy MainWindow
        super().mouseDoubleClickEvent(event)

    def apply_style(self, entity_style, attribute_style):
        self.entity_font = entity_style.font
        self.entity_color = entity_style.color
        self.attribute_font = attribute_style.font
        self.attribute_color = attribute_style.color

        if hasattr(self, 'title_item') and self.title_item:
            self.title_item.setFont(self.entity_font)
            self.title_item.setDefaultTextColor(self.entity_color)

        self.update_content()

    def mousePressEvent(self, event):
        self._initial_pos = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if hasattr(self, '_initial_pos') and self.pos() != self._initial_pos:
            from ...commands.move_command import MoveEntityCommand
            if self.scene() and self.scene().views():
                mw = self.scene().views()[0].window()
                if hasattr(mw, 'undo_stack'):
                    cmd = MoveEntityCommand(self, self._initial_pos, self.pos())
                    mw.undo_stack.push(cmd)