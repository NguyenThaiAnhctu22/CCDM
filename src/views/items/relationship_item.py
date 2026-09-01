import math
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem, QStyle
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF
from PySide6.QtGui import QPen, QColor, QPainterPath, QFont, QPainterPathStroker

from .entity_item import EntityItem
from ..dialogs.relationship_dialog import RelationshipDialog
from ...helpers.erd_symbols import draw_erd_symbol


class DraggableLabelItem(QGraphicsTextItem):
    """Text Item đại diện tên Relationship giữ offset tương đối so với đường dây"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.setDefaultTextColor(QColor("#000000"))
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.custom_offset = QPointF(-15, -20)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        parent_rel = self.parentItem()
        if parent_rel and hasattr(parent_rel, 'get_mid_point'):
            mid_p = parent_rel.get_mid_point()
            if mid_p:
                current_pos = self.pos()
                self.custom_offset = QPointF(
                    current_pos.x() - mid_p.x(), 
                    current_pos.y() - mid_p.y()
                )
                if hasattr(parent_rel, 'rel_model') and parent_rel.rel_model:
                    parent_rel.rel_model.label_offset_x = self.custom_offset.x()
                    parent_rel.rel_model.label_offset_y = self.custom_offset.y()

    def mouseDoubleClickEvent(self, event):
        # Label là item con riêng, nằm đè lên đường dây -> double click vào label không tự
        # lan tới RelationshipItem cha. Ủy quyền lại để mở cùng dialog chỉnh sửa Relationship.
        parent_rel = self.parentItem()
        if parent_rel and hasattr(parent_rel, 'mouseDoubleClickEvent'):
            parent_rel.mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)


def distance_to_segment(p: QPointF, l1: QPointF, l2: QPointF) -> float:
    line = QLineF(l1, l2)
    if line.length() == 0:
        return QLineF(p, l1).length()
    
    u = ((p.x() - l1.x()) * (l2.x() - l1.x()) + (p.y() - l1.y()) * (l2.y() - l1.y())) / (line.length() ** 2)
    u = max(0.0, min(1.0, u))
    
    proj_p = QPointF(l1.x() + u * (l2.x() - l1.x()), l1.y() + u * (l2.y() - l1.y()))
    return QLineF(p, proj_p).length()


def get_side_direction_vector(side: str) -> QPointF:
    if side == 'LEFT': return QPointF(-1.0, 0.0)
    elif side == 'RIGHT': return QPointF(1.0, 0.0)
    elif side == 'TOP': return QPointF(0.0, -1.0)
    else: return QPointF(0.0, 1.0)


def get_closest_side_and_point(entity_item: EntityItem, scene_pos: QPointF) -> tuple[str, QPointF]:
    rect = entity_item.sceneBoundingRect() if hasattr(entity_item, 'sceneBoundingRect') else entity_item.mapRectToScene(entity_item.rect())
    
    clamped_x = max(rect.left() + 5, min(rect.right() - 5, scene_pos.x()))
    clamped_y = max(rect.top() + 5, min(rect.bottom() - 5, scene_pos.y()))

    dist_left = abs(scene_pos.x() - rect.left())
    dist_right = abs(scene_pos.x() - rect.right())
    dist_top = abs(scene_pos.y() - rect.top())
    dist_bottom = abs(scene_pos.y() - rect.bottom())

    min_dist = min(dist_left, dist_right, dist_top, dist_bottom)

    if min_dist == dist_left: return 'LEFT', QPointF(rect.left(), clamped_y)
    elif min_dist == dist_right: return 'RIGHT', QPointF(rect.right(), clamped_y)
    elif min_dist == dist_top: return 'TOP', QPointF(clamped_x, rect.top())
    else: return 'BOTTOM', QPointF(clamped_x, rect.bottom())


def _effective_side(r, entity_item) -> str:
    if r.source_item == entity_item:
        if r.source_side:
            return r.source_side
        s_side, _ = calculate_dynamic_sides(r.source_item, r.target_item)
        return s_side
    else:
        if r.target_side:
            return r.target_side
        _, t_side = calculate_dynamic_sides(r.source_item, r.target_item)
        return t_side


def get_distributed_anchor_point(entity_item: EntityItem, side: str, rel_item, offset: QPointF = QPointF(0, 0)) -> QPointF:
    rect = entity_item.sceneBoundingRect() if hasattr(entity_item, 'sceneBoundingRect') else entity_item.mapRectToScene(entity_item.rect())
    
    same_side_rels = []
    if hasattr(entity_item, 'relations'):
        same_side_rels = [
            r for r in entity_item.relations 
            if _effective_side(r, entity_item) == side
        ]

    total = max(1, len(same_side_rels))
    idx = same_side_rels.index(rel_item) if rel_item in same_side_rels else 0

    if side in ('LEFT', 'RIGHT'):
        step = rect.height() / (total + 1)
        base_y = rect.top() + step * (idx + 1) + offset.y()
        clamped_y = max(rect.top() + 8.0, min(rect.bottom() - 8.0, base_y))
        return QPointF(rect.left() if side == 'LEFT' else rect.right(), clamped_y)
    else:
        step = rect.width() / (total + 1)
        base_x = rect.left() + step * (idx + 1) + offset.x()
        clamped_x = max(rect.left() + 8.0, min(rect.right() - 8.0, base_x))
        return QPointF(clamped_x, rect.top() if side == 'TOP' else rect.bottom())


def simplify_path_points(raw_points: list[QPointF]) -> list[QPointF]:
    if len(raw_points) <= 2: return raw_points

    cleaned = [raw_points[0]]
    for p in raw_points[1:]:
        if QLineF(cleaned[-1], p).length() > 2.0:
            cleaned.append(p)

    if len(cleaned) <= 2: return cleaned

    simplified = [cleaned[0]]
    for i in range(1, len(cleaned) - 1):
        prev_p, curr_p, next_p = simplified[-1], cleaned[i], cleaned[i + 1]
        is_horiz = abs(prev_p.y() - curr_p.y()) < 0.5 and abs(curr_p.y() - next_p.y()) < 0.5
        is_vert = abs(prev_p.x() - curr_p.x()) < 0.5 and abs(curr_p.x() - next_p.x()) < 0.5
        if not (is_horiz or is_vert):
            simplified.append(curr_p)

    simplified.append(cleaned[-1])
    return simplified


def calculate_dynamic_sides(src_item: EntityItem, tgt_item: EntityItem) -> tuple[str, str]:
    src_rect = src_item.sceneBoundingRect()
    tgt_rect = tgt_item.sceneBoundingRect()

    overlap_x = min(src_rect.right(), tgt_rect.right()) - max(src_rect.left(), tgt_rect.left())
    if overlap_x > 0:
        return ('BOTTOM', 'TOP') if src_rect.center().y() < tgt_rect.center().y() else ('TOP', 'BOTTOM')

    overlap_y = min(src_rect.bottom(), tgt_rect.bottom()) - max(src_rect.top(), tgt_rect.top())
    if overlap_y > 0:
        return ('RIGHT', 'LEFT') if src_rect.center().x() < tgt_rect.center().x() else ('LEFT', 'RIGHT')

    dx = tgt_rect.center().x() - src_rect.center().x()
    dy = tgt_rect.center().y() - src_rect.center().y()

    s_horiz = 'RIGHT' if dx > 0 else 'LEFT'
    t_horiz = 'LEFT' if dx > 0 else 'RIGHT'
    s_vert = 'BOTTOM' if dy > 0 else 'TOP'
    t_vert = 'TOP' if dy > 0 else 'BOTTOM'

    if abs(dx) >= abs(dy):
        return s_horiz, t_vert
    else:
        return s_vert, t_horiz


def check_line_intersects_rect(p1: QPointF, p2: QPointF, rect: QRectF) -> bool:
    padded_rect = rect.adjusted(-5, -5, 5, 5)
    
    if max(p1.x(), p2.x()) < padded_rect.left() or min(p1.x(), p2.x()) > padded_rect.right():
        return False
    if max(p1.y(), p2.y()) < padded_rect.top() or min(p1.y(), p2.y()) > padded_rect.bottom():
        return False

    if abs(p1.x() - p2.x()) < 0.1:
        return padded_rect.left() <= p1.x() <= padded_rect.right() and \
               not (max(p1.y(), p2.y()) <= padded_rect.top() or min(p1.y(), p2.y()) >= padded_rect.bottom())
    if abs(p1.y() - p2.y()) < 0.1:
        return padded_rect.top() <= p1.y() <= padded_rect.bottom() and \
               not (max(p1.x(), p2.x()) <= padded_rect.left() or min(p1.x(), p2.x()) >= padded_rect.right())

    return False


def is_path_colliding_with_other_entities(raw_points: list[QPointF], rel_item) -> bool:
    if not rel_item.scene():
        return False

    src_item = rel_item.source_item
    tgt_item = rel_item.target_item

    other_entities = [
        item for item in rel_item.scene().items()
        if isinstance(item, EntityItem) and item not in (src_item, tgt_item)
    ]

    for i in range(len(raw_points) - 1):
        p1, p2 = raw_points[i], raw_points[i + 1]
        for entity in other_entities:
            entity_rect = entity.sceneBoundingRect()
            if check_line_intersects_rect(p1, p2, entity_rect):
                return True
    return False


def route_smart_manhattan(rel_item) -> tuple[list, str, str]:
    """Routing Manhattan CHUẨN - Hỗ trợ Liên kết tự thân (Self-Relationship) động theo mọi side."""
    src_item, tgt_item = rel_item.source_item, rel_item.target_item

    is_self_rel = (src_item == tgt_item) or (
        hasattr(rel_item, 'rel_model') and rel_item.rel_model and 
        rel_item.rel_model.source_id == rel_item.rel_model.target_id
    )

    if is_self_rel:
        s_side = rel_item.source_side if rel_item.source_side else 'TOP'
        t_side = rel_item.target_side if rel_item.target_side else 'RIGHT'
        
        rect = src_item.sceneBoundingRect() if hasattr(src_item, 'sceneBoundingRect') else src_item.mapRectToScene(src_item.rect())
        offset = getattr(rel_item, 'manual_offset', QPointF(0, 0))
        
        start_ratio = getattr(rel_item, 'self_start_ratio', 0.35)
        end_ratio = getattr(rel_item, 'self_end_ratio', 0.45)

        if s_side in ('TOP', 'BOTTOM'):
            start_x = rect.left() + rect.width() * start_ratio + offset.x()
            clamped_start_x = max(rect.left() + 8.0, min(rect.right() - 8.0, start_x))
            start_p = QPointF(clamped_start_x, rect.top() if s_side == 'TOP' else rect.bottom())
        else:
            start_y = rect.top() + rect.height() * start_ratio + offset.y()
            clamped_start_y = max(rect.top() + 8.0, min(rect.bottom() - 8.0, start_y))
            start_p = QPointF(rect.left() if s_side == 'LEFT' else rect.right(), clamped_start_y)

        if t_side in ('LEFT', 'RIGHT'):
            end_y = rect.top() + rect.height() * end_ratio + offset.y()
            clamped_end_y = max(rect.top() + 8.0, min(rect.bottom() - 8.0, end_y))
            end_p = QPointF(rect.left() if t_side == 'LEFT' else rect.right(), clamped_end_y)
        else:
            end_x = rect.left() + rect.width() * end_ratio + offset.x()
            clamped_end_x = max(rect.left() + 8.0, min(rect.right() - 8.0, end_x))
            end_p = QPointF(clamped_end_x, rect.top() if t_side == 'TOP' else rect.bottom())

        loop_offset = 35.0

        v_src = get_side_direction_vector(s_side)
        v_tgt = get_side_direction_vector(t_side)

        p1 = start_p + v_src * loop_offset
        p3 = end_p + v_tgt * loop_offset

        if s_side in ('TOP', 'BOTTOM') and t_side in ('LEFT', 'RIGHT'):
            p2 = QPointF(p3.x(), p1.y())
        elif s_side in ('LEFT', 'RIGHT') and t_side in ('TOP', 'BOTTOM'):
            p2 = QPointF(p1.x(), p3.y())
        elif s_side in ('TOP', 'BOTTOM') and t_side in ('TOP', 'BOTTOM'):
            mid_y = p1.y()
            p2 = QPointF(p3.x(), mid_y)
        else:
            mid_x = p1.x()
            p2 = QPointF(mid_x, p3.y())

        raw_points = [start_p, p1, p2, p3, end_p]
        return raw_points, s_side, t_side

    # -------------------------------------------------------------
    # Liên kết giữa 2 Entity khác nhau
    # -------------------------------------------------------------
    auto_s_side, auto_t_side = calculate_dynamic_sides(src_item, tgt_item)

    s_side = rel_item.source_side if rel_item.source_side else auto_s_side
    t_side = rel_item.target_side if rel_item.target_side else auto_t_side

    offset = getattr(rel_item, 'manual_offset', QPointF(0, 0))

    is_perpendicular = (s_side in ('LEFT', 'RIGHT') and t_side in ('TOP', 'BOTTOM')) or \
                       (s_side in ('TOP', 'BOTTOM') and t_side in ('LEFT', 'RIGHT'))

    if is_perpendicular:
        if s_side in ('LEFT', 'RIGHT'):
            effective_offset = QPointF(0.0, offset.y())
        else:
            effective_offset = QPointF(offset.x(), 0.0)
    else:
        effective_offset = offset

    start_p = get_distributed_anchor_point(src_item, s_side, rel_item, offset)
    end_p = get_distributed_anchor_point(tgt_item, t_side, rel_item, offset)

    ALIGN_TOLERANCE = 20.0

    raw_points = []

    if s_side in ('LEFT', 'RIGHT') and t_side in ('LEFT', 'RIGHT'):
        if abs(start_p.y() - end_p.y()) < ALIGN_TOLERANCE:
            # Không có góc vuông nào bắt buộc -> tự canh thẳng, bỏ qua offset đã kéo trước đó
            avg_y = (start_p.y() + end_p.y()) / 2.0
            start_p = QPointF(start_p.x(), avg_y)
            end_p = QPointF(end_p.x(), avg_y)
            raw_points = [start_p, end_p]
        else:
            mid_x = (start_p.x() + end_p.x()) / 2.0 + offset.x()
            raw_points = [start_p, QPointF(mid_x, start_p.y()), QPointF(mid_x, end_p.y()), end_p]

            if is_path_colliding_with_other_entities(raw_points, rel_item):
                for avoid_step in [60, -60, 120, -120, 180, -180]:
                    alt_mid_x = mid_x + avoid_step
                    alt_points = [start_p, QPointF(alt_mid_x, start_p.y()), QPointF(alt_mid_x, end_p.y()), end_p]
                    if not is_path_colliding_with_other_entities(alt_points, rel_item):
                        raw_points = alt_points
                        break

    elif s_side in ('TOP', 'BOTTOM') and t_side in ('TOP', 'BOTTOM'):
        if abs(start_p.x() - end_p.x()) < ALIGN_TOLERANCE:
            # Không có góc vuông nào bắt buộc -> tự canh thẳng theo chiều dọc, bỏ qua offset đã kéo trước đó
            avg_x = (start_p.x() + end_p.x()) / 2.0
            start_p = QPointF(avg_x, start_p.y())
            end_p = QPointF(avg_x, end_p.y())
            raw_points = [start_p, end_p]
        else:
            mid_y = (start_p.y() + end_p.y()) / 2.0 + offset.y()
            raw_points = [start_p, QPointF(start_p.x(), mid_y), QPointF(end_p.x(), mid_y), end_p]

            if is_path_colliding_with_other_entities(raw_points, rel_item):
                for avoid_step in [60, -60, 120, -120, 180, -180]:
                    alt_mid_y = mid_y + avoid_step
                    alt_points = [start_p, QPointF(start_p.x(), alt_mid_y), QPointF(end_p.x(), alt_mid_y), end_p]
                    if not is_path_colliding_with_other_entities(alt_points, rel_item):
                        raw_points = alt_points
                        break

    else:
        if s_side in ('LEFT', 'RIGHT'):
            corner = QPointF(end_p.x(), start_p.y())
        else:
            corner = QPointF(start_p.x(), end_p.y())
        raw_points = [start_p, corner, end_p]
        
    return simplify_path_points(raw_points), s_side, t_side


class RelationshipItem(QGraphicsPathItem):
    def __init__(self, rel_model, source_item: EntityItem, target_item: EntityItem, parent=None):
        super().__init__(parent)
        self.rel_model = rel_model
        self.source_item = source_item
        self.target_item = target_item

        self.setFlags(QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPen(QPen(QColor("#06B423"), 1, Qt.PenStyle.SolidLine))
        self.setZValue(1)

        self.source_side = getattr(self.rel_model, 'source_side', None)
        self.target_side = getattr(self.rel_model, 'target_side', None)
        
        self.self_start_ratio = getattr(self.rel_model, 'self_start_ratio', 0.35)
        self.self_end_ratio = getattr(self.rel_model, 'self_end_ratio', 0.45)
        
        offset_x = getattr(self.rel_model, 'manual_offset_x', 0.0)
        offset_y = getattr(self.rel_model, 'manual_offset_y', 0.0)
        self.manual_offset = QPointF(offset_x, offset_y)

        self.drag_mode = None
        self.is_dragging = False
        self.preview_points = []
        self.drag_start_pos = None

        name = getattr(self.rel_model, 'name', '')
        self.label_item = DraggableLabelItem(name, self)

        lbl_x = getattr(self.rel_model, 'label_offset_x', -15.0)
        lbl_y = getattr(self.rel_model, 'label_offset_y', -20.0)
        self.label_item.custom_offset = QPointF(lbl_x, lbl_y)

        if hasattr(self.source_item, 'relations') and self not in self.source_item.relations:
            self.source_item.relations.append(self)
        if hasattr(self.target_item, 'relations') and self not in self.target_item.relations:
            self.target_item.relations.append(self)

        self.rel_model.source_cardinality = getattr(self.rel_model, 'source_cardinality', "One-Optional")
        self.rel_model.target_cardinality = getattr(self.rel_model, 'target_cardinality', "Many-Optional")

        self.update_position()
        self.setZValue(1)

    def is_self_relationship(self) -> bool:
        return (self.source_item == self.target_item) or (
            hasattr(self, 'rel_model') and self.rel_model and 
            self.rel_model.source_id == self.rel_model.target_id
        )

    def get_mid_point(self) -> QPointF:
        points, _, _ = route_smart_manhattan(self)
        if len(points) < 2:
            return QPointF(0, 0)

        # Tính trung điểm theo độ dài thực của đường dây (points thô, KHÔNG gồm ký hiệu ERD
        # như chân gà/vòng tròn/tam giác). Nếu dùng self.path().pointAtPercent(0.5) như trước,
        # độ dài các ký hiệu ERD (được vẽ chung vào path) sẽ làm lệch điểm 50%, khiến label
        # bị "nhảy" ra sát đầu dây và bị che khi hình dạng đường thay đổi lúc kéo entity.
        seg_lengths = [QLineF(points[i], points[i + 1]).length() for i in range(len(points) - 1)]
        total = sum(seg_lengths)

        if total <= 0:
            return points[0]

        half = total / 2.0
        accum = 0.0
        for i, seg_len in enumerate(seg_lengths):
            if accum + seg_len >= half:
                ratio = (half - accum) / seg_len if seg_len > 0 else 0.0
                p1, p2 = points[i], points[i + 1]
                return QPointF(
                    p1.x() + (p2.x() - p1.x()) * ratio,
                    p1.y() + (p2.y() - p1.y()) * ratio
                )
            accum += seg_len

        return points[-1]

    def mousePressEvent(self, event):
        scene_pos = event.scenePos()
        points, _, _ = route_smart_manhattan(self)
        self.drag_mode = None
        
        if len(points) >= 2:
            dist_src = QLineF(scene_pos, points[0]).length()
            dist_tgt = QLineF(scene_pos, points[-1]).length()

            if dist_src <= 22.0:
                self.drag_mode = 'source'
            elif dist_tgt <= 22.0:
                self.drag_mode = 'target'
            else:
                num_segments = len(points) - 1

                if num_segments == 1:
                    pass
                elif num_segments == 2:
                    if distance_to_segment(scene_pos, points[0], points[1]) <= 12.0:
                        self.drag_mode = 'seg_1'
                elif num_segments == 3:
                    if distance_to_segment(scene_pos, points[0], points[1]) <= 12.0:
                        self.drag_mode = 'seg_1'
                    elif distance_to_segment(scene_pos, points[1], points[2]) <= 12.0:
                        self.drag_mode = 'seg_2'
                elif num_segments > 3:
                    mid_idx = num_segments // 2
                    if distance_to_segment(scene_pos, points[mid_idx], points[mid_idx + 1]) <= 12.0:
                        self.drag_mode = 'seg_2'

            if self.drag_mode:
                self.is_dragging = True
                self.drag_start_pos = scene_pos
                self.preview_points = list(points)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_dragging and self.drag_mode:
            scene_pos = event.scenePos()
            
            if self.drag_mode in ('seg_1', 'seg_2'):
                is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if is_shift:
                    temp_offset = QPointF(0.0, 0.0)   # Ép về đường thẳng mặc định
                else:
                    delta = scene_pos - self.drag_start_pos
                    temp_offset = self.manual_offset + delta
                
                old_offset = self.manual_offset
                self.manual_offset = temp_offset
                self.preview_points, _, _ = route_smart_manhattan(self)
                self.manual_offset = old_offset
            elif self.drag_mode == 'source':
                side, pt = get_closest_side_and_point(self.source_item, scene_pos)
                self.preview_points = [pt] + list(self.preview_points[1:])
            elif self.drag_mode == 'target':
                side, pt = get_closest_side_and_point(self.target_item, scene_pos)
                self.preview_points = list(self.preview_points[:-1]) + [pt]

            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_dragging and self.drag_mode:
            scene_pos = event.scenePos()

            if self.drag_mode in ('seg_1', 'seg_2'):
                is_shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if is_shift:
                    self.manual_offset = QPointF(0.0, 0.0)   # Chốt lại thẳng, bỏ hết offset đã kéo
                else:
                    delta = scene_pos - self.drag_start_pos
                    _, s_side, t_side = route_smart_manhattan(self)
                    is_perpendicular = (s_side in ('LEFT', 'RIGHT') and t_side in ('TOP', 'BOTTOM')) or \
                                       (s_side in ('TOP', 'BOTTOM') and t_side in ('LEFT', 'RIGHT'))

                    if is_perpendicular:
                        if s_side in ('LEFT', 'RIGHT'):
                            self.manual_offset += QPointF(0.0, delta.y())
                        else:
                            self.manual_offset += QPointF(delta.x(), 0.0)
                    else:
                        if self.drag_mode == 'seg_1':
                            if s_side in ('LEFT', 'RIGHT'):
                                self.manual_offset += QPointF(0.0, delta.y())
                            else:
                                self.manual_offset += QPointF(delta.x(), 0.0)
                        elif self.drag_mode == 'seg_2':
                            if s_side in ('LEFT', 'RIGHT'):
                                self.manual_offset += QPointF(delta.x(), 0.0)
                            else:
                                self.manual_offset += QPointF(0.0, delta.y())

                    if QLineF(QPointF(0, 0), self.manual_offset).length() < 10.0:
                        self.manual_offset = QPointF(0.0, 0.0)

                self.rel_model.manual_offset_x = self.manual_offset.x()
                self.rel_model.manual_offset_y = self.manual_offset.y()

            elif self.drag_mode == 'source':
                side, pt = get_closest_side_and_point(self.source_item, scene_pos)
                self.source_side = side
                self.rel_model.source_side = side

                if self.is_self_relationship():
                    rect = self.source_item.sceneBoundingRect()
                    if side in ('TOP', 'BOTTOM'):
                        ratio = (pt.x() - rect.left()) / max(1.0, rect.width())
                    else:
                        ratio = (pt.y() - rect.top()) / max(1.0, rect.height())
                    
                    self.self_start_ratio = max(0.05, min(0.95, ratio))
                    self.rel_model.self_start_ratio = self.self_start_ratio

            elif self.drag_mode == 'target':
                side, pt = get_closest_side_and_point(self.target_item, scene_pos)
                self.target_side = side
                self.rel_model.target_side = side

                if self.is_self_relationship():
                    rect = self.target_item.sceneBoundingRect()
                    if side in ('LEFT', 'RIGHT'):
                        ratio = (pt.y() - rect.top()) / max(1.0, rect.height())
                    else:
                        ratio = (pt.x() - rect.left()) / max(1.0, rect.width())

                    self.self_end_ratio = max(0.05, min(0.95, ratio))
                    self.rel_model.self_end_ratio = self.self_end_ratio

            self.is_dragging = False
            self.drag_mode = None
            self.preview_points = []
            self.drag_start_pos = None
            self.update_position()

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        event.accept()

        # Ưu tiên gọi qua MainWindow.open_relationship_dialog (nếu có) để đồng bộ Undo snapshot
        # với đường mở dialog từ Object Browser / double-click vào Label.
        main_window = None
        if self.scene() and self.scene().views():
            main_window = self.scene().views()[0].window()

        if main_window and hasattr(main_window, 'open_relationship_dialog'):
            main_window.open_relationship_dialog(self)
            return

        # Fallback: mở dialog trực tiếp (không có Undo) nếu không tìm được MainWindow
        src_name = getattr(getattr(self.source_item, 'entity', None), 'name', None) or getattr(self.source_item, 'name', "Source Entity")
        tgt_name = getattr(getattr(self.target_item, 'entity', None), 'name', None) or getattr(self.target_item, 'name', "Target Entity")

        parent_widget = self.scene().views()[0] if self.scene() and self.scene().views() else None

        dialog = RelationshipDialog(self.rel_model, src_name, tgt_name, rel_item=self, parent=parent_widget)
        
        if dialog.exec():
            data = dialog.get_data()
            self.rel_model.name = data["name"]
            self.rel_model.source_cardinality = data["source_cardinality"]
            self.rel_model.target_cardinality = data["target_cardinality"]
            
            self.rel_model.is_dependent_source = data.get("is_dependent_source", False)
            self.rel_model.is_dependent_target = data.get("is_dependent_target", False)

            if hasattr(self, 'label_item') and self.label_item:
                self.label_item.setPlainText(data["name"])
            self.update_position()

    def update_position(self):
        if not self.source_item or not self.target_item:
            return

        points, s_side, t_side = route_smart_manhattan(self)
        if len(points) < 2:
            return

        src_dir = get_side_direction_vector(s_side)
        tgt_dir = get_side_direction_vector(t_side)

        src_card = getattr(self.rel_model, 'source_cardinality', 'One-Optional')
        tgt_card = getattr(self.rel_model, 'target_cardinality', 'Many-Optional')

        is_dep_src = getattr(self.rel_model, 'is_dependent_source', False)
        is_dep_tgt = getattr(self.rel_model, 'is_dependent_target', False)

        path = QPainterPath()

        # 1. Vẽ ký hiệu ERD tại 2 đầu neo
        reach_src = draw_erd_symbol(path, points[0], src_dir, src_card, is_dependent=is_dep_tgt)
        reach_tgt = draw_erd_symbol(path, points[-1], tgt_dir, tgt_card, is_dependent=is_dep_src)

        wire_start = points[0] + src_dir * reach_src
        wire_end = points[-1] + tgt_dir * reach_tgt

        # 2. Xử lý đường dây vẽ bo tròn góc nếu là Self-Relationship
        if self.is_self_relationship() and len(points) >= 5:
            corner_radius = 8.0
            path.moveTo(wire_start)
            
            p_curr_entry = wire_start
            for i in range(1, len(points) - 1):
                p_prev = points[i-1] if i == 1 else p_curr_entry
                p_curr = points[i]
                p_next = points[i+1]
                
                v_in = QLineF(p_prev, p_curr).unitVector()
                v_out = QLineF(p_curr, p_next).unitVector()
                
                p_entry = p_curr - QPointF(v_in.dx(), v_in.dy()) * corner_radius
                p_exit = p_curr + QPointF(v_out.dx(), v_out.dy()) * corner_radius
                
                path.lineTo(p_entry)
                path.quadTo(p_curr, p_exit)
                p_curr_entry = p_exit

            path.lineTo(wire_end)
        else:
            wire_points = [wire_start] + points[1:-1] + [wire_end]
            path.moveTo(wire_points[0])
            for p in wire_points[1:]:
                path.lineTo(p)

        self.setPath(path)

        # 3. Cập nhật vị trí Label
        if hasattr(self, 'label_item') and self.label_item:
            if self.is_self_relationship() and len(points) >= 3:
                # Định vị Label tại trung điểm đoạn ở giữa (p1->p2 hoặc p2->p3 tùy thuộc cạnh neo)
                mid_segment_p1 = points[1]
                mid_segment_p2 = points[2]
                center_x = (mid_segment_p1.x() + mid_segment_p2.x()) / 2.0
                center_y = (mid_segment_p1.y() + mid_segment_p2.y()) / 2.0
                
                # Tự động đẩy Label ra ngoài tùy theo s_side
                lbl_w = self.label_item.boundingRect().width()
                lbl_h = self.label_item.boundingRect().height()
                
                if s_side == 'TOP':
                    pos_x = center_x - lbl_w / 2
                    pos_y = center_y - lbl_h - 4.0
                elif s_side == 'BOTTOM':
                    pos_x = center_x - lbl_w / 2
                    pos_y = center_y + 4.0
                elif s_side == 'LEFT':
                    pos_x = center_x - lbl_w - 4.0
                    pos_y = center_y - lbl_h / 2
                else: # RIGHT
                    pos_x = center_x + 4.0
                    pos_y = center_y - lbl_h / 2
                    
                self.label_item.setPos(QPointF(pos_x, pos_y))
            else:
                mid_p = self.get_mid_point()
                rect = self.label_item.boundingRect()
                self.label_item.setTransformOriginPoint(rect.center())
                new_label_pos = mid_p + self.label_item.custom_offset
                self.label_item.setPos(new_label_pos)

        self.update()

    def apply_style(self, rel_style):
        if hasattr(self, 'label_item') and self.label_item:
            self.label_item.setFont(rel_style.font)
            self.label_item.setDefaultTextColor(rel_style.color)

        line_width = getattr(rel_style, 'line_width', 1)
        line_color = getattr(rel_style, 'line_color', QColor("#06B423"))
        self.setPen(QPen(line_color, line_width, Qt.PenStyle.SolidLine))

        self.update_position()

    def boundingRect(self) -> QRectF:
        rect = super().boundingRect()
        margin = 15.0
        return rect.adjusted(-margin, -margin, margin, margin)

    def paint(self, painter, option, widget=None):
        opt = option.__class__(option)
        opt.state &= ~QStyle.StateFlag.State_Selected

        super().paint(painter, opt, widget)

        if self.is_dragging and self.preview_points:
            painter.save()
            dash_pen = QPen(QColor("#0080FF"), 1.8, Qt.PenStyle.DashLine)
            painter.setPen(dash_pen)

            prev_path = QPainterPath()
            prev_path.moveTo(self.preview_points[0])
            for p in self.preview_points[1:]:
                prev_path.lineTo(p)

            painter.drawPath(prev_path)
            painter.restore()

        if self.isSelected():
            points, _, _ = route_smart_manhattan(self)
            painter.save()
            painter.setPen(QPen(QColor("#000000"), 1, Qt.PenStyle.SolidLine))
            painter.setBrush(QColor("#000000"))

            handle_size = 6.0
            half_size = handle_size / 2.0

            for p in points:
                handle_rect = QRectF(p.x() - half_size, p.y() - half_size, handle_size, handle_size)
                painter.drawRect(handle_rect)

            painter.restore()

    def shape(self) -> QPainterPath:
        points, _, _ = route_smart_manhattan(self)
        line_path = QPainterPath()
        if points:
            line_path.moveTo(points[0])
            for p in points[1:]:
                line_path.lineTo(p)

        stroker = QPainterPathStroker()
        stroker.setWidth(14.0)
        stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
        stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return stroker.createStroke(line_path)