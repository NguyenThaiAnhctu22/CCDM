from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QDialogButtonBox, QLabel, QTabWidget, QWidget, QGroupBox, QRadioButton,
    QCheckBox, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QGraphicsPathItem, QTextEdit, QPushButton
)
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QColor, QFont, QPainterPath, QBrush

from ...helpers.erd_symbols import draw_erd_symbol
from ...helpers.cardinality_helper import CardinalityHelper


class RelationshipPreviewWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setMinimumHeight(120)
        self.setMaximumHeight(140)
        self.setStyleSheet("background-color: #ffffff; border: 1px solid #c0c0c0;")
        
        self.scene.setSceneRect(0, 0, 400, 100)
        
        self.src_name = "Entity_1"
        self.tgt_name = "Entity_2"
        # ĐẶT MẶC ĐỊNH MỚI: Entity 1 là "0,n", Entity 2 là "0,1"
        self.card1 = "0,n"
        self.card2 = "0,1"
        self.is_dep1 = False
        self.is_dep2 = False

    def update_preview(self, src_name: str, tgt_name: str, card1: str, card2: str, is_dep1: bool = False, is_dep2: bool = False):
        self.src_name = src_name if src_name else "Entity_1"
        self.tgt_name = tgt_name if tgt_name else "Entity_2"
        self.card1 = card1  # Card phía Entity_1
        self.card2 = card2  # Card phía Entity_2
        self.is_dep1 = is_dep2
        self.is_dep2 = is_dep1
        self.redraw()

    def redraw(self):
        self.scene.clear()

        # 1. Entity_1 (Bên trái)
        e1_rect = QGraphicsRectItem(0, 0, 110, 50)
        e1_rect.setPen(QPen(QColor("#008080"), 1.5))
        e1_rect.setBrush(QBrush(QColor("#e0ffff")))
        e1_rect.setPos(15, 25)
        self.scene.addItem(e1_rect)

        t1 = QGraphicsTextItem(self.src_name.replace("_", "_ "))
        t1.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t1.setDefaultTextColor(QColor("#000000"))
        t1.setTextWidth(100)
        fmt1 = t1.document().defaultTextOption()
        fmt1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.document().setDefaultTextOption(fmt1)
        self.scene.addItem(t1)
        t1.setPos(20, 25 + (50 - t1.boundingRect().height()) / 2)

        # 2. Entity_2 (Bên phải)
        e2_rect = QGraphicsRectItem(0, 0, 110, 50)
        e2_rect.setPen(QPen(QColor("#008080"), 1.5))
        e2_rect.setBrush(QBrush(QColor("#e0ffff")))
        e2_rect.setPos(275, 25)
        self.scene.addItem(e2_rect)

        t2 = QGraphicsTextItem(self.tgt_name.replace("_", "_ "))
        t2.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        t2.setDefaultTextColor(QColor("#000000"))
        t2.setTextWidth(100)
        fmt2 = t2.document().defaultTextOption()
        fmt2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t2.document().setDefaultTextOption(fmt2)
        self.scene.addItem(t2)
        t2.setPos(280, 25 + (50 - t2.boundingRect().height()) / 2)

        # 3. Đường nối
        p1 = QPointF(125, 50)  # Mép sát Entity_1
        p2 = QPointF(275, 50)  # Mép sát Entity_2
        path = QPainterPath()
        path.moveTo(p1)
        path.lineTo(p2)

        # ==============================================================================
        # ĐỦ ĐIỀU KIỆN CHUẨN CANVAS:
        # - p1 (mép Entity 1): Vẽ ký hiệu theo card2 (Entity_2 to Entity_1)
        # - p2 (mép Entity 2): Vẽ ký hiệu theo card1 (Entity_1 to Entity_2)
        # ==============================================================================
        draw_erd_symbol(path, p1, QPointF(1, 0), self.card2, is_dependent=self.is_dep2)
        draw_erd_symbol(path, p2, QPointF(-1, 0), self.card1, is_dependent=self.is_dep1)

        path_item = QGraphicsPathItem(path)
        path_item.setPen(QPen(QColor("#008080"), 1.5))
        self.scene.addItem(path_item)


class RelationshipDialog(QDialog):
    def __init__(self, rel_model, src_name: str, tgt_name: str, rel_item=None, parent=None):
        super().__init__(parent)
        self._is_updating = False
        self.rel_model = rel_model
        self.rel_item = rel_item
        
        self.src_name = src_name if src_name else "Entity_1"
        self.tgt_name = tgt_name if tgt_name else "Entity_2"

        rel_name = getattr(rel_model, 'name', 'rel_1')
        rel_code = getattr(rel_model, 'code', getattr(rel_model, 'id', 'REL_1'))
        
        self.setWindowTitle(f"Relationship Properties - {rel_name} ({rel_code})")
        self.resize(540, 620)

        main_layout = QVBoxLayout(self)

        top_btn_layout = QHBoxLayout()
        self.btn_top_e1 = QPushButton(f"  {self.src_name}  ")
        self.btn_top_e2 = QPushButton(f"  {self.tgt_name}  ")
        top_btn_layout.addWidget(self.btn_top_e1)
        top_btn_layout.addWidget(self.btn_top_e2)
        main_layout.addLayout(top_btn_layout)

        self.preview_widget = RelationshipPreviewWidget(self)
        main_layout.addWidget(self.preview_widget)

        self.tabs = QTabWidget()

        # TAB GENERAL
        general_tab = QWidget()
        gen_layout = QFormLayout(general_tab)
        gen_layout.setContentsMargins(10, 15, 10, 10)

        self.txt_gen_name = QLineEdit(rel_name)
        gen_layout.addRow("Name:", self.txt_gen_name)

        self.txt_gen_code = QLineEdit(rel_code)
        gen_layout.addRow("Code:", self.txt_gen_code)

        self.txt_comment = QTextEdit()
        self.txt_comment.setMaximumHeight(70)
        gen_layout.addRow("Comment:", self.txt_comment)

        self.cb_entity1 = QComboBox()
        self.cb_entity1.addItem(f"  {self.src_name}")
        self.cb_entity1.setEnabled(False)
        gen_layout.addRow("Entity 1:", self.cb_entity1)

        self.cb_entity2 = QComboBox()
        self.cb_entity2.addItem(f"  {self.tgt_name}")
        self.cb_entity2.setEnabled(False)
        gen_layout.addRow("Entity 2:", self.cb_entity2)

        # TAB CARDINALITIES
        card_tab = QWidget()
        card_layout = QVBoxLayout(card_tab)

        self.lbl_description = QLabel()
        self.lbl_description.setStyleSheet("color: #333333; font-style: italic;")
        card_layout.addWidget(self.lbl_description)

        gb_card = QGroupBox("Cardinalities")
        gb_card_layout = QVBoxLayout(gb_card)
        rb_layout = QHBoxLayout()
        self.rb_11 = QRadioButton("One - One")
        self.rb_1n = QRadioButton("One - Many")
        self.rb_n1 = QRadioButton("Many - One")
        self.rb_nn = QRadioButton("Many - Many")

        rb_layout.addWidget(self.rb_11)
        rb_layout.addWidget(self.rb_1n)
        rb_layout.addWidget(self.rb_n1)
        rb_layout.addWidget(self.rb_nn)
        gb_card_layout.addLayout(rb_layout)
        card_layout.addWidget(gb_card)

        # GroupBox: Entity_1 to Entity_2
        self.gb_e1_e2 = QGroupBox(f"{self.src_name} to {self.tgt_name}")
        fl_e1 = QFormLayout(self.gb_e1_e2)
        self.txt_role1 = QLineEdit(getattr(rel_model, 'role1_name', ''))
        fl_e1.addRow("Role name:", self.txt_role1)

        opt1_layout = QHBoxLayout()
        self.chk_dep1 = QCheckBox("Dependent")
        self.chk_man1 = QCheckBox("Mandatory")
        self.cb_card1 = QComboBox()
        self.cb_card1.addItems(["0,1", "1,1", "0,n", "1,n"])

        opt1_layout.addWidget(self.chk_dep1)
        opt1_layout.addWidget(self.chk_man1)
        opt1_layout.addWidget(QLabel("Cardinality:"))
        opt1_layout.addWidget(self.cb_card1)
        fl_e1.addRow(opt1_layout)
        card_layout.addWidget(self.gb_e1_e2)

        # GroupBox: Entity_2 to Entity_1
        self.gb_e2_e1 = QGroupBox(f"{self.tgt_name} to {self.src_name}")
        fl_e2 = QFormLayout(self.gb_e2_e1)
        self.txt_role2 = QLineEdit(getattr(rel_model, 'role2_name', ''))
        fl_e2.addRow("Role name:", self.txt_role2)

        opt2_layout = QHBoxLayout()
        self.chk_dep2 = QCheckBox("Dependent")
        self.chk_man2 = QCheckBox("Mandatory")
        self.cb_card2 = QComboBox()
        self.cb_card2.addItems(["0,1", "1,1", "0,n", "1,n"])

        opt2_layout.addWidget(self.chk_dep2)
        opt2_layout.addWidget(self.chk_man2)
        opt2_layout.addWidget(QLabel("Cardinality:"))
        opt2_layout.addWidget(self.cb_card2)
        fl_e2.addRow(opt2_layout)
        card_layout.addWidget(self.gb_e2_e1)

        self.tabs.addTab(general_tab, "General")
        self.tabs.addTab(card_tab, "Cardinalities")
        self.tabs.addTab(QWidget(), "Notes")
        self.tabs.addTab(QWidget(), "Rules")
        main_layout.addWidget(self.tabs)

        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel | 
            QDialogButtonBox.StandardButton.Apply
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_changes)
        main_layout.addWidget(btn_box)

        self._init_data()
        self._connect_signals()
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _init_data(self):
        self._is_updating = True

        src_c = getattr(self.rel_model, 'source_cardinality', 'One-Optional')
        tgt_c = getattr(self.rel_model, 'target_cardinality', 'Many-Optional')

        # CHÚ Ý ĐỔI TẠI ĐÂY: 
        # Entity_1 to Entity_2 đọc theo ký hiệu kế bên Entity_2 (tgt_c = Many -> 0,n)
        # Entity_2 to Entity_1 đọc theo ký hiệu kế bên Entity_1 (src_c = One -> 0,1)
        self.chk_man1.setChecked("Mandatory" in tgt_c)
        self.chk_man2.setChecked("Mandatory" in src_c)

        self.cb_card1.setCurrentText(CardinalityHelper.model_to_combo_string(tgt_c))  # Hiện 0,n
        self.cb_card2.setCurrentText(CardinalityHelper.model_to_combo_string(src_c))  # Hiện 0,1

        self.chk_dep1.setChecked(getattr(self.rel_model, 'is_dependent_target', False))
        self.chk_dep2.setChecked(getattr(self.rel_model, 'is_dependent_source', False))

        is_src_many = "Many" in src_c
        is_tgt_many = "Many" in tgt_c

        if not is_src_many and not is_tgt_many:
            self.rb_11.setChecked(True)
        elif not is_src_many and is_tgt_many:
            self.rb_1n.setChecked(True)  # One - Many (1-N)
        elif is_src_many and not is_tgt_many:
            self.rb_n1.setChecked(True)  # Many - One (N-1)
        else:
            self.rb_nn.setChecked(True)  # Many - Many (N-N)

        self._is_updating = False

    def _connect_signals(self):
        self.txt_gen_name.textChanged.connect(self._on_name_changed)
        self.txt_gen_code.textChanged.connect(self._update_window_title)

        self.rb_11.toggled.connect(self._on_rb_changed)
        self.rb_1n.toggled.connect(self._on_rb_changed)
        self.rb_n1.toggled.connect(self._on_rb_changed)
        self.rb_nn.toggled.connect(self._on_rb_changed)

        self.chk_dep1.toggled.connect(self._on_dep1_toggled)
        self.chk_dep2.toggled.connect(self._on_dep2_toggled)

        self.chk_man1.toggled.connect(self._on_chk1_changed)
        self.chk_man2.toggled.connect(self._on_chk2_changed)

        self.cb_card1.currentIndexChanged.connect(self._on_cb1_changed)
        self.cb_card2.currentIndexChanged.connect(self._on_cb2_changed)

    def _update_dependent_and_mandatory_states(self):
        is_c1_many = ",n" in self.cb_card1.currentText()
        is_c2_many = ",n" in self.cb_card2.currentText()

        # Dependent chỉ chọn được ở phía One (không áp dụng cho Many)
        if is_c1_many:
            self.chk_dep1.setChecked(False)
            self.chk_dep1.setEnabled(False)
        else:
            self.chk_dep1.setEnabled(True)

        if is_c2_many:
            self.chk_dep2.setChecked(False)
            self.chk_dep2.setEnabled(False)
        else:
            self.chk_dep2.setEnabled(True)

        # Khi tích Dependent thì Mandatory tự kích hoạt
        if self.chk_dep1.isChecked():
            self.chk_man1.setChecked(True)
            self.chk_man1.setEnabled(False)
        else:
            self.chk_man1.setEnabled(True)

        if self.chk_dep2.isChecked():
            self.chk_man2.setChecked(True)
            self.chk_man2.setEnabled(False)
        else:
            self.chk_man2.setEnabled(True)

    def _on_dep1_toggled(self, checked: bool):
        if self._is_updating: return
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _on_dep2_toggled(self, checked: bool):
        if self._is_updating: return
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _on_name_changed(self, text: str):
        code_text = text.upper().replace(" ", "_")
        self.txt_gen_code.setText(code_text)
        self._update_window_title()

    def _update_window_title(self):
        name = self.txt_gen_name.text().strip()
        code = self.txt_gen_code.text().strip()
        self.setWindowTitle(f"Relationship Properties - {name} ({code})")

    def _on_rb_changed(self):
        if self._is_updating: return
        self._is_updating = True
        
        if self.rb_11.isChecked():
            self.cb_card1.setCurrentText("1,1" if self.chk_man1.isChecked() else "0,1")
            self.cb_card2.setCurrentText("1,1" if self.chk_man2.isChecked() else "0,1")
        elif self.rb_1n.isChecked(): # One - Many
            # CHÚ Ý ĐỔI TẠI ĐÂY:
            self.cb_card1.setCurrentText("1,n" if self.chk_man1.isChecked() else "0,n") # Entity_1 to Entity_2
            self.cb_card2.setCurrentText("1,1" if self.chk_man2.isChecked() else "0,1") # Entity_2 to Entity_1
        elif self.rb_n1.isChecked(): # Many - One
            self.cb_card1.setCurrentText("1,1" if self.chk_man1.isChecked() else "0,1")
            self.cb_card2.setCurrentText("1,n" if self.chk_man2.isChecked() else "0,n")
        elif self.rb_nn.isChecked(): # Many - Many
            self.cb_card1.setCurrentText("1,n" if self.chk_man1.isChecked() else "0,n")
            self.cb_card2.setCurrentText("1,n" if self.chk_man2.isChecked() else "0,n")
            
        self._is_updating = False
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _on_chk1_changed(self):
        if self._is_updating: return
        self._is_updating = True
        is_man = self.chk_man1.isChecked()
        is_many = ",n" in self.cb_card1.currentText()
        self.cb_card1.setCurrentText(("1,n" if is_many else "1,1") if is_man else ("0,n" if is_many else "0,1"))
        self._is_updating = False
        self._on_values_changed()

    def _on_chk2_changed(self):
        if self._is_updating: return
        self._is_updating = True
        is_man = self.chk_man2.isChecked()
        is_many = ",n" in self.cb_card2.currentText()
        self.cb_card2.setCurrentText(("1,n" if is_many else "1,1") if is_man else ("0,n" if is_many else "0,1"))
        self._is_updating = False
        self._on_values_changed()

    def _on_cb1_changed(self):
        if self._is_updating: return
        self._is_updating = True
        text = self.cb_card1.currentText()
        self.chk_man1.setChecked("1," in text)
        self._is_updating = False
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _on_cb2_changed(self):
        if self._is_updating: return
        self._is_updating = True
        text = self.cb_card2.currentText()
        self.chk_man2.setChecked("1," in text)
        self._is_updating = False
        self._update_dependent_and_mandatory_states()
        self._on_values_changed()

    def _on_values_changed(self):
        if self._is_updating: return
            
        c1 = self.cb_card1.currentText()
        c2 = self.cb_card2.currentText()

        desc1 = CardinalityHelper.get_cardinality_description(self.src_name, self.tgt_name, c1)
        desc2 = CardinalityHelper.get_cardinality_description(self.tgt_name, self.src_name, c2)
        self.lbl_description.setText(f"{desc1}\n{desc2}")

        self.preview_widget.update_preview(
            self.src_name, self.tgt_name, c1, c2, 
            self.chk_dep1.isChecked(), self.chk_dep2.isChecked()
        )

    def get_data(self) -> dict:
        c1 = self.cb_card1.currentText() # Entity 1 to Entity 2 (đáp ứng phía Target)
        c2 = self.cb_card2.currentText() # Entity 2 to Entity 1 (đáp ứng phía Source)

        return {
            "name": self.txt_gen_name.text().strip(),
            "code": self.txt_gen_code.text().strip(),
            "source_cardinality": CardinalityHelper.combo_to_model_string(self.chk_man2.isChecked(), c2),
            "target_cardinality": CardinalityHelper.combo_to_model_string(self.chk_man1.isChecked(), c1),
            "is_dependent_source": self.chk_dep2.isChecked(),
            "is_dependent_target": self.chk_dep1.isChecked()
        }

    def apply_changes(self):
        data = self.get_data()
        self.rel_model.name = data["name"]
        if hasattr(self.rel_model, 'code'):
            self.rel_model.code = data["code"]

        # Đồng bộ ngược lại Canvas chuẩn xác
        self.rel_model.source_cardinality = data["source_cardinality"]
        self.rel_model.target_cardinality = data["target_cardinality"]
        self.rel_model.is_dependent_source = data["is_dependent_source"]
        self.rel_model.is_dependent_target = data["is_dependent_target"]

        if self.rel_item:
            if hasattr(self.rel_item, 'update_position'):
                self.rel_item.update_position()
            if self.rel_item.scene():
                self.rel_item.scene().update()

    def accept(self):
        self.apply_changes()
        super().accept()