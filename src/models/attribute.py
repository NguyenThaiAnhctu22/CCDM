import uuid
from typing import Optional

class Attribute:
    def __init__(self, name: str, data_type: str, is_pk: bool = False, is_fk: bool = False, 
                 is_nullable: bool = True, attr_id: Optional[str] = None):
        self.id = attr_id or str(uuid.uuid4())  # Tự động tạo UUID nếu chưa có ID
        self.name = name
        self.data_type = data_type
        self.is_pk = is_pk
        self.is_fk = is_fk
        self.is_nullable = is_nullable

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "data_type": self.data_type,
            "is_pk": self.is_pk,
            "is_fk": self.is_fk,
            "is_nullable": self.is_nullable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Attribute":
        return cls(
            attr_id=data.get("id"),
            name=data["name"],
            data_type=data.get("data_type", ""),
            is_pk=data.get("is_pk", False),
            is_fk=data.get("is_fk", False),
            is_nullable=data.get("is_nullable", True)
        )