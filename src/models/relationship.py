from typing import Dict, Any


class Relationship:
    def __init__(
        self, 
        id: str, 
        source_id: str, 
        target_id: str, 
        name: str = "", 
        source_cardinality: str = "One-Optional", 
        target_cardinality: str = "Many-Optional",
        is_dependent_source: bool = False,
        is_dependent_target: bool = False,
        code: str = "",
        # Bổ sung thông tin Layout/Vị trí
        label_offset_x: float = -15.0,
        label_offset_y: float = -20.0,
        manual_offset_x: float = 0.0,
        manual_offset_y: float = 0.0,
        source_side: str = None,
        target_side: str = None,
        # SỬA LỖI 1: Đã khai báo tham số tự thân vào signature của __init__
        self_start_ratio: float = 0.35,
        self_end_ratio: float = 0.45
    ):
        self.id = id
        self.source_id = source_id
        self.target_id = target_id
        self.name = name if name else f"rel_{id}"
        self.code = code if code else self.name.upper()
        self.source_cardinality = source_cardinality
        self.target_cardinality = target_cardinality
        self.is_dependent_source = is_dependent_source
        self.is_dependent_target = is_dependent_target

        # Thuộc tính lưu trữ layout
        self.label_offset_x = label_offset_x
        self.label_offset_y = label_offset_y
        self.manual_offset_x = manual_offset_x
        self.manual_offset_y = manual_offset_y
        self.source_side = source_side
        self.target_side = target_side

        # Thuộc tính Self-Relationship
        self.self_start_ratio = self_start_ratio
        self.self_end_ratio = self_end_ratio

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "name": self.name,
            "code": self.code,
            "source_cardinality": self.source_cardinality,
            "target_cardinality": self.target_cardinality,
            "is_dependent_source": self.is_dependent_source,
            "is_dependent_target": self.is_dependent_target,
            # Xuất dữ liệu vị trí ra dict
            "label_offset_x": self.label_offset_x,
            "label_offset_y": self.label_offset_y,
            "manual_offset_x": self.manual_offset_x,
            "manual_offset_y": self.manual_offset_y,
            "source_side": self.source_side,
            "target_side": self.target_side,
            # Lưu tỷ lệ vị trí neo cho liên kết tự thân
            "self_start_ratio": self.self_start_ratio,
            "self_end_ratio": self.self_end_ratio
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Relationship":
        return cls(
            id=data.get("id", ""),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            name=data.get("name", ""),
            code=data.get("code", ""),
            source_cardinality=data.get("source_cardinality", "One-Optional"),
            target_cardinality=data.get("target_cardinality", "Many-Optional"),
            is_dependent_source=data.get("is_dependent_source", False),
            is_dependent_target=data.get("is_dependent_target", False),
            # Phục hồi dữ liệu vị trí từ dict
            label_offset_x=data.get("label_offset_x", -15.0),
            label_offset_y=data.get("label_offset_y", -20.0),
            manual_offset_x=data.get("manual_offset_x", 0.0),
            manual_offset_y=data.get("manual_offset_y", 0.0),
            source_side=data.get("source_side", None),
            target_side=data.get("target_side", None),
            # SỬA LỖI 2: Đọc dữ liệu tự thân khi load file project cũ/mới
            self_start_ratio=data.get("self_start_ratio", 0.35),
            self_end_ratio=data.get("self_end_ratio", 0.45)
        )

    @classmethod
    def create_default(cls, rel_id: str, source_id: str, target_id: str) -> "Relationship":
        """Khởi tạo quan hệ chuẩn 1-N (Source = 1, Target = N)"""
        return cls(
            id=rel_id,
            source_id=source_id,
            target_id=target_id,
            name="",
            source_cardinality="One-Optional",
            target_cardinality="Many-Optional",
            is_dependent_source=False,
            is_dependent_target=False
        )