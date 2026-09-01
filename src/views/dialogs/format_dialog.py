from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, 
    QLabel, QPushButton, QFontDialog, QColorDialog, QDialogButtonBox, QCheckBox,
    QSpinBox, QFrame
)
from PySide6.QtGui import QFont, QColor

class FormatStyle:
    def __init__(
        self,
        font=QFont("Readdex Pro", 13)
        .setStyleName("Deca Light"),
        color=QColor("#000000"),
        line_width: int = 1,
        line_color=QColor("#1f5ca9"),
    ):
        self.font = font
        self.color = color
        # Chỉ thực sự được dùng cho category "relationship" (độ dày & màu đường kẻ)
        self.line_width = line_width
        self.line_color = line_color if isinstance(line_color, QColor) else QColor(line_color)

    def to_dict(self):
        """Xuất dữ liệu style ra dict để lưu JSON vào file model .ccdm"""
        return {
            "family": self.font.family(),
            "point_size": self.font.pointSize(),
            "bold": self.font.bold(),
            "italic": self.font.italic(),
            "color": self.color.name(),
            "line_width": self.line_width,
            "line_color": self.line_color.name(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Khôi phục FormatStyle từ dict trong file .ccdm"""
        if not data:
            return cls()
        font = QFont(data.get("family", "Readdex Pro"), data.get("point_size", 13))
        if "style_name" in data and data["style_name"]:
            font.setStyleName(data["style_name"])
        else:
            # Fallback về bold/italic nếu không có style_name
            font.setBold(data.get("bold", False))
            font.setItalic(data.get("italic", False))
        color = QColor(data.get("color", "#000000"))
        line_width = data.get("line_width", 1)
        line_color = QColor(data.get("line_color", "#1f5ca9"))
        return cls(font, color, line_width, line_color)


class FormatDialog(QDialog):
    def __init__(self, current_styles: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tùy chỉnh Định dạng Font & Màu sắc")
        self.resize(420, 360)

        # Sao chép style hiện tại để chỉnh sửa (bao gồm cả line_width/line_color)
        def _copy_style(src: FormatStyle) -> FormatStyle:
            return FormatStyle(
                QFont(src.font),
                QColor(src.color),
                getattr(src, "line_width", 1),
                QColor(getattr(src, "line_color", QColor("#1f5ca9"))),
            )

        self.styles = {
            "entity": _copy_style(current_styles["entity"]),
            "attribute": _copy_style(current_styles["attribute"]),
            "relationship": _copy_style(current_styles["relationship"]),
        }

        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        self.tab_widget.addTab(self._create_style_tab("entity"), "Entity")
        self.tab_widget.addTab(self._create_style_tab("attribute"), "Attributes")
        self.tab_widget.addTab(self._create_style_tab("relationship"), "Relationship")

        layout.addWidget(self.tab_widget)

        # Thêm Checkbox hỏi có lưu làm mặc định hệ thống không
        self.chk_save_as_default = QCheckBox("Đặt làm màu sắc & font mặc định cho các file tạo mới sau này")
        layout.addWidget(self.chk_save_as_default)

        # Hàng chứa nút bấm: Reset Mặc định + OK / Cancel
        btn_layout = QHBoxLayout()

        btn_reset = QPushButton("Đặt lại mặc định")
        btn_reset.clicked.connect(self._reset_to_defaults)
        btn_layout.addWidget(btn_reset)

        btn_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        btn_layout.addWidget(button_box)

        layout.addLayout(btn_layout)

    def _reset_to_defaults(self):
        """Khôi phục lại Font chữ, Màu sắc và Kích thước về giá trị gốc của phần mềm"""
        # 1. Khai báo lại style mặc định ban đầu
        default_entity_font = QFont("Readex Pro", 13)
        default_entity_font.setStyleName("Deca Light")

        default_rel_font = QFont("Readex Pro", 12)
        default_rel_font.setStyleName("Deca Light")

        self.styles = {
            "entity": FormatStyle(default_entity_font, QColor("#000000")),
            "attribute": FormatStyle(QFont(default_entity_font), QColor("#000000")),
            "relationship": FormatStyle(
                default_rel_font, QColor("#000000"), line_width=1, line_color=QColor("#1f5ca9")
            ),
        }

        # 2. Vẽ lại nội dung các Tab để cập nhật giao diện
        current_index = self.tab_widget.currentIndex()
        self.tab_widget.clear()
        self.tab_widget.addTab(self._create_style_tab("entity"), "Entity")
        self.tab_widget.addTab(self._create_style_tab("attribute"), "Attributes")
        self.tab_widget.addTab(self._create_style_tab("relationship"), "Relationship")
        self.tab_widget.setCurrentIndex(current_index)

    def _create_style_tab(self, category_key: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        style = self.styles[category_key]

        lbl_preview = QLabel("Mẫu văn bản xem trước (Sample Text)")
        lbl_preview.setFont(style.font)
        lbl_preview.setStyleSheet(f"color: {style.color.name()}; border: 1px solid #ccc; padding: 10px;")
        lbl_preview.setMinimumHeight(60)

        btn_font = QPushButton("Chọn Font / Cỡ chữ / Độ đậm")
        def choose_font():
            ok, font = QFontDialog.getFont(style.font, self, "Chọn Font chữ")
            if ok:
                style.font = font
                lbl_preview.setFont(font)
        btn_font.clicked.connect(choose_font)

        btn_color = QPushButton("Chọn Màu sắc Văn bản")
        def choose_color():
            color = QColorDialog.getColor(style.color, self, "Chọn Màu sắc")
            if color.isValid():
                style.color = color
                lbl_preview.setStyleSheet(f"color: {color.name()}; border: 1px solid #ccc; padding: 10px;")
        btn_color.clicked.connect(choose_color)

        layout.addWidget(lbl_preview)
        layout.addWidget(btn_font)
        layout.addWidget(btn_color)

        # Chỉ hiển thị tùy chọn Đường kẻ (Line) cho tab Relationship
        if category_key == "relationship":
            line_preview = QFrame()
            line_preview.setFixedHeight(40)

            def update_line_preview():
                line_preview.setStyleSheet(
                    f"border: none; border-top: {style.line_width}px solid {style.line_color.name()}; "
                    f"margin-top: 19px;"
                )
            update_line_preview()

            lbl_line_title = QLabel("Đường kẻ Relationship (Line)")
            lbl_line_title.setStyleSheet("font-weight: bold; margin-top: 8px;")

            row_width = QHBoxLayout()
            lbl_width = QLabel("Độ dày (px):")
            spin_width = QSpinBox()
            spin_width.setRange(1, 10)
            spin_width.setValue(style.line_width)

            def change_width(value):
                style.line_width = value
                update_line_preview()
            spin_width.valueChanged.connect(change_width)

            row_width.addWidget(lbl_width)
            row_width.addWidget(spin_width)
            row_width.addStretch()

            btn_line_color = QPushButton("Chọn Màu Đường Kẻ")

            def choose_line_color():
                color = QColorDialog.getColor(style.line_color, self, "Chọn Màu Đường Kẻ")
                if color.isValid():
                    style.line_color = color
                    update_line_preview()
            btn_line_color.clicked.connect(choose_line_color)

            layout.addSpacing(10)
            layout.addWidget(lbl_line_title)
            layout.addWidget(line_preview)
            layout.addLayout(row_width)
            layout.addWidget(btn_line_color)

        layout.addStretch()

        return widget

    def get_styles(self) -> dict:
        return self.styles

    def is_save_as_default(self) -> bool:
        return self.chk_save_as_default.isChecked()