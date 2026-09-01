from typing import Dict, List, Any
from .entity import Entity
from .relationship import Relationship


class Project:
    def __init__(self, name: str = "Untitled Project"):
        self.name = name
        self.entities: Dict[str, Entity] = {}
        self.relationships: List[Relationship] = []
        self.styles = None
        self.simplified_mode = False

    def add_entity(self, entity: Entity) -> None:
        self.entities[entity.id] = entity

    def remove_entity(self, entity_id: str) -> None:
        if entity_id in self.entities:
            del self.entities[entity_id]
            self.relationships = [
                r for r in self.relationships 
                if r.source_id != entity_id and r.target_id != entity_id
            ]

    def add_relationship(self, relationship: Relationship) -> None:
        self.relationships.append(relationship)

    def remove_relationship(self, rel_id: str) -> None:
        self.relationships = [r for r in self.relationships if r.id != rel_id]

    def create_relationship(self, source_id: str, target_id: str) -> Relationship:
        rel_id = f"rel_{len(self.relationships) + 1}"
        rel = Relationship.create_default(rel_id, source_id, target_id)
        self.add_relationship(rel)
        return rel

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "entities": [e.to_dict() for e in self.entities.values()],
            "relationships": [r.to_dict() for r in self.relationships],
            "styles": self.styles,
            "simplified_mode": self.simplified_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        project = cls(name=data.get("name", "Untitled Project"))
        project.styles = data.get("styles", None)
        project.simplified_mode = data.get("simplified_mode", False)
        
        for e_data in data.get("entities", []):
            entity = Entity.from_dict(e_data)
            project.add_entity(entity)
        for r_data in data.get("relationships", []):
            project.add_relationship(Relationship.from_dict(r_data))
            
        return project