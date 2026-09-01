from typing import List, Optional
from .attribute import Attribute

class Entity:
    def __init__(self, name: str, entity_id: Optional[str] = None, x: float = 0.0, y: float = 0.0,
                 custom_width: Optional[float] = None, custom_height: Optional[float] = None):
        self.id = entity_id or name
        self.name = name
        self.attributes: List[Attribute] = []
        self.x = x
        self.y = y
        # Lưu kích thước thủ công (nếu người dùng kéo thay đổi kích thước)
        self.custom_width = custom_width
        self.custom_height = custom_height

    def add_attribute(self, attr: Attribute) -> None:
        self.attributes.append(attr)

    def remove_attribute(self, attr_id_or_name: str) -> None:
        self.attributes = [a for a in self.attributes if a.id != attr_id_or_name and a.name != attr_id_or_name]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "custom_width": self.custom_width,
            "custom_height": self.custom_height,
            "attributes": [attr.to_dict() for attr in self.attributes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        entity = cls(
            name=data["name"], 
            entity_id=data.get("id"), 
            x=data.get("x", 0.0), 
            y=data.get("y", 0.0),
            custom_width=data.get("custom_width"),
            custom_height=data.get("custom_height")
        )
        entity.attributes = [Attribute.from_dict(attr) for attr in data.get("attributes", [])]
        return entity