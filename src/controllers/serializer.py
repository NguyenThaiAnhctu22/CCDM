import json
from ..models.project import Project

class Serializer:
    @staticmethod
    def save_to_file(project: Project, file_path: str) -> bool:
        """Lưu toàn bộ Project (bao gồm cả styles & simplified_mode) ra file JSON (.ccdm)"""
        try:
            data = project.to_dict() if hasattr(project, 'to_dict') else {
                "name": project.name,
                "entities": [e.to_dict() for e in project.entities.values()],
                "relationships": [r.to_dict() for r in project.relationships],
                "styles": getattr(project, "styles", None),
                "simplified_mode": getattr(project, "simplified_mode", False)
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"Lỗi khi lưu file: {e}")
            return False

    @staticmethod
    def load_from_file(file_path: str) -> Project:
        """Đọc file JSON (.ccdm) và phục hồi đối tượng Project kèm theo styles & simplified_mode"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        if hasattr(Project, 'from_dict'):
            return Project.from_dict(data)
        
        # Fallback thủ công nếu Project chưa hỗ trợ from_dict
        project = Project(name=data.get("name", "Untitled Project"))
        project.styles = data.get("styles", None)
        project.simplified_mode = data.get("simplified_mode", False)
        return project