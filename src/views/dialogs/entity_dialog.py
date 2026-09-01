from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QTableWidget, 
    QTableWidgetItem, QPushButton, QComboBox, QCheckBox, QHeaderView, QWidget
)
from PySide6.QtCore import Qt
from ...models.entity import Entity
from ...models.attribute import Attribute
from ...helpers.translations import TRANSLATIONS

class EntityDialog(QDialog):
    def __init__(self, entity: Entity, auto_prefix: bool = False, parent=None):
        super().__init__(parent)
        self.entity = entity
        self.auto_prefix = auto_prefix

        # 1. Lấy ngôn ngữ từ Parent (MainWindow) hoặc mặc định là "en"
        self.current_lang = getattr(parent, "current_lang", "en") if parent else "en"
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])

        # 2. Tiêu đề cửa sổ theo ngôn ngữ
        self.setWindowTitle(t.get("dlg_entity_title", "Edit Entity: {}").format(entity.name))
        self.resize(650, 450)
        
        layout = QVBoxLayout(self)
        
        # Tên Entity
        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        self.name_input = QLineEdit(entity.name)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Nếu bật auto_prefix -> Bắt sự kiện gõ tên Entity để Format UPPER_CASE
        if self.auto_prefix:
            self.name_input.textChanged.connect(self._on_entity_name_changed)
        
        # Bảng danh sách Attribute (5 cột)
        self.table = QTableWidget(0, 5)
        headers = [
            t.get("table_col_name", "Name"),
            t.get("table_col_type", "Data Type"),
            t.get("table_col_pk", "PK"),
            t.get("table_col_fk", "FK"),
            t.get("table_col_null", "Nullable")
        ]
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Nút Thêm / Xóa / Di chuyển hàng
        btn_layout = QHBoxLayout()
        add_btn = QPushButton(t.get("btn_add_attr", "Add Attribute"))
        add_btn.clicked.connect(self._add_row)
        remove_btn = QPushButton(t.get("btn_remove_attr", "Delete Selected"))
        remove_btn.clicked.connect(self._remove_row)
        
        move_up_btn = QPushButton(t.get("btn_move_up", "▲ Up"))
        move_up_btn.clicked.connect(self._move_row_up)
        move_down_btn = QPushButton(t.get("btn_move_down", "▼ Down"))
        move_down_btn.clicked.connect(self._move_row_down)

        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        btn_layout.addWidget(move_up_btn)
        btn_layout.addWidget(move_down_btn)
        layout.addLayout(btn_layout)
        
        # Nút OK / Cancel
        dialog_btns = QHBoxLayout()
        save_btn = QPushButton(t.get("btn_save", "Save"))
        save_btn.clicked.connect(self._save_and_accept)
        cancel_btn = QPushButton(t.get("btn_cancel", "Cancel"))
        cancel_btn.clicked.connect(self.reject)
        dialog_btns.addWidget(save_btn)
        dialog_btns.addWidget(cancel_btn)
        layout.addLayout(dialog_btns)

        self.table.installEventFilter(self)
        self.table.currentCellChanged.connect(self._on_current_cell_changed)

        # Tắt autoDefault cho các nút phụ để tránh nhận nhầm sự kiện Enter
        add_btn.setAutoDefault(False)
        remove_btn.setAutoDefault(False)
        move_up_btn.setAutoDefault(False)
        move_down_btn.setAutoDefault(False)
        cancel_btn.setAutoDefault(False)

        # Đặt nút Lưu là nút Default chính thức (Bấm Enter ở bất kỳ ô input nào cũng sẽ Save)
        save_btn.setDefault(True)
        
        self._load_data()

        self._check_and_select_default_name()

    def _check_and_select_default_name(self):
        """Kiểm tra nếu tên Entity là tên mặc định thì tự động tô bôi đen toàn bộ"""
        current_name = self.name_input.text().strip()
        
        # Kiểm tra theo định dạng tên mặc định (bắt đầu bằng Entity_ hoặc bằng ID nếu tên gán mặc định bằng ID)
        is_default = (
            current_name.startswith("Entity_") or 
            current_name.lower() == str(self.entity.id).lower()
        )
        
        if is_default:
            self.name_input.setFocus()
            self.name_input.selectAll()

    def _on_current_cell_changed(self, row: int, col: int, previous_row: int, previous_col: int):
        """Khi người dùng chuyển ô (bằng Tab/Mũi tên), tự động Focus vào Checkbox hoặc ComboBox nếu có"""
        if col in [2, 3, 4] and row >= 0:
            cb = self._get_checkbox_from_cell(row, col)
            if cb:
                cb.setFocus()

    def eventFilter(self, source, event):
        if event.type() == event.Type.KeyPress:
            key = event.key()
            current_row = self.table.currentRow()
            current_col = self.table.currentColumn()
            total_rows = self.table.rowCount()
            total_cols = self.table.columnCount()

            # 1. Bắt phím Tab ở ô cuối cùng (hàng cuối, cột 4 - Nullable)
            if key == Qt.Key.Key_Tab:
                if current_row == total_rows - 1 and current_col == total_cols - 1:
                    self._add_row()
                    return True  # Đã xử lý, chặn Tab mặc định nhảy ra khỏi bảng

            # 2. Xử lý phím Space khi đang ở các ô Checkbox (Cột 2, 3, 4)
            elif key == Qt.Key.Key_Space:
                if current_col in [2, 3, 4] and current_row >= 0:
                    cb = self._get_checkbox_from_cell(current_row, current_col)
                    if cb and cb.isEnabled():
                        cb.toggle()
                        return True

        return super().eventFilter(source, event)

    def _get_attribute_prefix(self) -> str:
        """Hàm tính toán tiền tố dựa trên tên Entity hiện tại"""
        raw_name = self.name_input.text().strip()
        if not raw_name:
            return ""
        
        words = [w for w in raw_name.split('_') if w]
        if len(words) >= 2:
            # KHACH_HANG -> KH_
            prefix = "".join([w[0] for w in words]).upper()
        else:
            # KHACH -> KH_
            clean_word = words[0]
            prefix = clean_word[:2].upper() if len(clean_word) >= 2 else clean_word.upper()
            
        return f"{prefix}_" if prefix else ""

    def _on_entity_name_changed(self, text: str):
        """Tự động viết hoa và thay khoảng trắng bằng dấu gạch dưới"""
        formatted_text = text.upper().replace(" ", "_")
        if formatted_text != text:
            # Giữ nguyên vị trí con trỏ nhập liệu
            cursor_pos = self.name_input.cursorPosition()
            self.name_input.setText(formatted_text)
            self.name_input.setCursorPosition(cursor_pos)

    def _create_centered_checkbox(self, checked: bool = False) -> tuple[QWidget, QCheckBox]:
        """Tạo QWidget chứa QCheckBox được căn giữa ô"""
        container = QWidget()
        checkbox = QCheckBox()
        checkbox.setChecked(checked)

        checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        layout = QHBoxLayout(container)
        layout.addWidget(checkbox)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)
        
        return container, checkbox

    def _get_checkbox_from_cell(self, row: int, col: int) -> QCheckBox:
        """Lấy QCheckBox ra từ QWidget wrapper ở ô chỉ định"""
        widget = self.table.cellWidget(row, col)
        if widget:
            return widget.findChild(QCheckBox)
        return None

    def _load_data(self):
        for attr in self.entity.attributes:
            self._add_row(attr)

    def _add_row(self, attr: Attribute = None):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Xác định tên thuộc tính mặc định
        if attr:
            attr_name = attr.name
        else:
            # Nếu tạo dòng mới và có bật auto_prefix -> Tự điền tiền tố (VD: KH_)
            attr_name = self._get_attribute_prefix() if self.auto_prefix else ""
        
        name_item = QTableWidgetItem(attr_name)
        type_cb = QComboBox()
        type_cb.addItems(["<Undefined>", "INT", "VARCHAR(50)", "VARCHAR(255)", "TEXT", "BOOLEAN", "DATETIME", "FLOAT"])
        if attr:
            type_cb.setCurrentText(attr.data_type)
            

        is_pk = attr.is_pk if attr else False
        is_fk = attr.is_fk if attr else False
        is_nullable = attr.is_nullable if attr else False

        pk_container, pk_cb = self._create_centered_checkbox(is_pk)
        fk_container, fk_cb = self._create_centered_checkbox(is_fk)
        null_container, null_cb = self._create_centered_checkbox(is_nullable)

        # Đăng ký eventFilter để nhận diện Tab/Space ngay tại Checkbox
        pk_cb.installEventFilter(self)
        fk_cb.installEventFilter(self)
        null_cb.installEventFilter(self)

        # Xử lý khóa chính: Nếu chọn PK -> Tự bỏ chọn Nullable và khóa ô check
        if is_pk:
            null_cb.setChecked(False)
            null_cb.setEnabled(False)

        # Định nghĩa hàm callback khi toggle PK
        def on_pk_changed(state):
            if state == 2:  # Qt.CheckState.Checked
                null_cb.setChecked(False)
                null_cb.setEnabled(False)
            else:
                null_cb.setEnabled(True)

        pk_cb.stateChanged.connect(on_pk_changed)

        self.table.setItem(row, 0, name_item)
        self.table.setCellWidget(row, 1, type_cb)
        self.table.setCellWidget(row, 2, pk_container)
        self.table.setCellWidget(row, 3, fk_container)
        self.table.setCellWidget(row, 4, null_container)

        # Nếu tạo mới khi bấm nút, focus vào ô tên vừa tạo
        if not attr:
            self.table.setCurrentCell(row, 0)
            
            # Mở editor cho ô hiện tại
            self.table.editItem(name_item)
            
            # Lấy widget QLineEdit đang active trong ô để bỏ chọn toàn bộ chữ (bỏ highlight xanh)
            editor = self.table.indexWidget(self.table.currentIndex())
            if not editor:
                editor = self.focusWidget() # Lấy editor hiện tại của QTableWidget
                
            if isinstance(editor, QLineEdit):
                # Đưa con trỏ xuống cuối văn bản (sau tiền tố như KH_) và bỏ bôi đen
                editor.setCursorPosition(len(editor.text()))
                editor.deselect()

    def _remove_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _swap_rows(self, row1: int, row2: int):
        """Tráo đổi dữ liệu giữa 2 hàng trong QTableWidget"""
        # Lấy dữ liệu row 1
        name1 = self.table.item(row1, 0).text()
        type1 = self.table.cellWidget(row1, 1).currentText()
        pk1_cb = self._get_checkbox_from_cell(row1, 2)
        fk1_cb = self._get_checkbox_from_cell(row1, 3)
        null1_cb = self._get_checkbox_from_cell(row1, 4)

        pk1, fk1, null1 = pk1_cb.isChecked(), fk1_cb.isChecked(), null1_cb.isChecked()

        # Lấy dữ liệu row 2
        name2 = self.table.item(row2, 0).text()
        type2 = self.table.cellWidget(row2, 1).currentText()
        pk2_cb = self._get_checkbox_from_cell(row2, 2)
        fk2_cb = self._get_checkbox_from_cell(row2, 3)
        null2_cb = self._get_checkbox_from_cell(row2, 4)

        pk2, fk2, null2 = pk2_cb.isChecked(), fk2_cb.isChecked(), null2_cb.isChecked()

        # Cập nhật row 1 bằng data row 2
        self.table.item(row1, 0).setText(name2)
        self.table.cellWidget(row1, 1).setCurrentText(type2)
        pk1_cb.setChecked(pk2)
        fk1_cb.setChecked(fk2)
        null1_cb.setChecked(null2)
        null1_cb.setEnabled(not pk2)

        # Cập nhật row 2 bằng data row 1
        self.table.item(row2, 0).setText(name1)
        self.table.cellWidget(row2, 1).setCurrentText(type1)
        pk2_cb.setChecked(pk1)
        fk2_cb.setChecked(fk1)
        null2_cb.setChecked(null1)
        null2_cb.setEnabled(not pk1)

    def _move_row_up(self):
        row = self.table.currentRow()
        if row > 0:
            self._swap_rows(row, row - 1)
            self.table.setCurrentCell(row - 1, 0)

    def _move_row_down(self):
        row = self.table.currentRow()
        if row >= 0 and row < self.table.rowCount() - 1:
            self._swap_rows(row, row + 1)
            self.table.setCurrentCell(row + 1, 0)

    def _save_and_accept(self):
        self.entity.name = self.name_input.text().strip() or self.entity.name
        self.entity.attributes.clear()
        
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            if not name:
                continue
            data_type = self.table.cellWidget(row, 1).currentText()
            
            pk_cb = self._get_checkbox_from_cell(row, 2)
            fk_cb = self._get_checkbox_from_cell(row, 3)
            null_cb = self._get_checkbox_from_cell(row, 4)

            is_pk = pk_cb.isChecked() if pk_cb else False
            is_fk = fk_cb.isChecked() if fk_cb else False
            is_nullable = null_cb.isChecked() if null_cb else False
            
            self.entity.add_attribute(Attribute(name, data_type, is_pk, is_fk, is_nullable))
            
        self.accept()