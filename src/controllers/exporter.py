import sys
import os
from PySide6.QtGui import QPainter, QImage, QColor
from PySide6.QtCore import QRectF, Qt
from PySide6.QtWidgets import QGraphicsScene, QMessageBox
from PySide6.QtSvg import QSvgGenerator
from ..models.project import Project

class Exporter:
    @staticmethod
    def export_to_image(scene: QGraphicsScene, file_path: str, white_background: bool = True, target_width: int = 6000) -> bool:
        """Xuất sơ đồ ra ảnh nét căng cao cấp (Ưu tiên theo thứ tự: PNG -> JPG -> EMF -> SVG)"""
        try:
            rect = scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
            if rect.isEmpty():
                rect = QRectF(0, 0, 1200, 800)

            ext = file_path.lower().split('.')[-1]

            # =========================================================================
            # 1. ƯU TIÊN 1, 2, 3: ĐỊNH DẠNG RASTER & RASTER-BASED EMF (PNG, JPG, EMF)
            # =========================================================================
            if ext in ("png", "jpg", "jpeg", "emf"):
                MIN_SCALE = 5.0
                scale = max(target_width / rect.width(), MIN_SCALE)
                
                img_w = int(rect.width() * scale)
                img_h = int(rect.height() * scale)

                use_alpha = (white_background is False) and (ext == "png")
                img_format = QImage.Format.Format_ARGB32 if use_alpha else QImage.Format.Format_RGB32
                
                image = QImage(img_w, img_h, img_format)
                image.setDevicePixelRatio(1.0)

                dpi = 96.0 * scale
                dots_per_meter = int(dpi / 0.0254)
                image.setDotsPerMeterX(dots_per_meter)
                image.setDotsPerMeterY(dots_per_meter)

                if use_alpha:
                    image.fill(0x00000000)
                else:
                    image.fill(0xFFFFFFFF)

                painter = QPainter(image)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
                painter.setRenderHint(QPainter.RenderHint.LosslessImageRendering, True)

                painter.scale(scale, scale)

                if white_background:
                    old_draw_bg = scene.drawBackground
                    scene.drawBackground = lambda p, r: None
                    scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
                    scene.drawBackground = old_draw_bg
                else:
                    scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)

                painter.end()

                if ext == "png":
                    return image.save(file_path, "PNG")
                elif ext in ("jpg", "jpeg"):
                    return image.save(file_path, "JPG", 100)
                elif ext == "emf":
                    return image.save(file_path, "PNG")

            # =========================================================================
            # 2. ƯU TIÊN 4: VECTƠ SVG
            # =========================================================================
            elif ext == "svg":
                generator = QSvgGenerator()
                generator.setFileName(file_path)
                generator.setSize(rect.size().toSize())
                generator.setViewBox(rect)

                painter = QPainter(generator)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

                if white_background:
                    old_draw_bg = scene.drawBackground
                    scene.drawBackground = lambda p, r: None
                    scene.render(painter, QRectF(rect), rect)
                    scene.drawBackground = old_draw_bg
                else:
                    scene.render(painter, QRectF(rect), rect)

                painter.end()
                return True

            return False

        except Exception as e:
            print(f"Lỗi khi xuất ảnh: {e}")
            return False

    @staticmethod
    def _export_high_res_emf(scene, file_path, rect, white_background):
        """Tạo file hình ảnh độ phân giải siêu cao (scale 3x) cho định dạng .emf"""
        try:
            scale = 3.0
            image = QImage(int(rect.width() * scale), int(rect.height() * scale), QImage.Format.Format_ARGB32)
            image.fill(0xFFFFFF)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.scale(scale, scale)

            if white_background:
                old_draw_bg = scene.drawBackground
                scene.drawBackground = lambda p, r: None
                scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)
                scene.drawBackground = old_draw_bg
            else:
                scene.render(painter, QRectF(0, 0, rect.width(), rect.height()), rect)

            painter.end()

            # Bắt buộc truyền format là "PNG" để QImage ghi dữ liệu ảnh nét cao vào file .emf thành công
            return image.save(file_path, "PNG")
        except Exception as e:
            print(f"Lỗi khi xuất EMF nét cao: {e}")
            return False

    @staticmethod
    def generate_sql_ddl(project: Project, dialect: str = "postgresql") -> str:
        """Chuyển đổi dữ liệu Project sang câu lệnh SQL DDL CREATE TABLE"""
        sql_lines = []
        
        for entity in project.entities.values():
            sql_lines.append(f"CREATE TABLE {entity.name.lower()} (")
            col_defs = []
            pk_list = []

            for attr in entity.attributes:
                nullable_str = "" if attr.is_nullable else " NOT NULL"
                col_defs.append(f"    {attr.name} {attr.data_type}{nullable_str}")
                if attr.is_pk:
                    pk_list.append(attr.name)

            if pk_list:
                col_defs.append(f"    PRIMARY KEY ({', '.join(pk_list)})")

            sql_lines.append(",\n".join(col_defs))
            sql_lines.append(");\n")

        return "\n".join(sql_lines)