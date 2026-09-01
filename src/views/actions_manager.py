# Trong src/views/actions_manager.py
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt
from ..helpers.translations import TRANSLATIONS
from .items.entity_item import EntityItem

class ActionsManager:
    def __init__(self, main_window):
        self.mw = main_window
        self.create_actions()

    def create_actions(self):
        mw = self.mw

        # 1. Khai báo các hành động cơ bản
        # Cập nhật Action cho New (Gán phím tắt Ctrl+N)
        mw.new_act = QAction(mw, triggered=mw.new_project)
        mw.new_act.setShortcut(QKeySequence.New)  # Tự động ăn Ctrl+N (Win/Linux) hoặc Cmd+N (Mac)
        mw.new_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        # Cập nhật Action cho Open (Gán phím tắt Ctrl+O)
        mw.open_act = QAction(mw, triggered=mw.open_project)
        mw.open_act.setShortcut(QKeySequence.Open)  # Tự động ăn Ctrl+O (Win/Linux) hoặc Cmd+O (Mac)
        mw.open_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        # 1. Cập nhật Action cho Save (Gán phím tắt Ctrl+S)
        mw.save_act = QAction(mw, triggered=mw.save_project)
        mw.save_act.setShortcut(QKeySequence.Save)  # Tự động ăn Ctrl+S (Windows/Linux) hoặc Cmd+S (Mac)
        mw.save_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        # 2. Thêm Action cho Save As (Gán phím tắt Ctrl+Shift+S)
        mw.save_as_act = QAction(mw, triggered=mw.save_project_as)
        mw.save_as_act.setShortcut(QKeySequence("Ctrl+Shift+S"))
        mw.save_as_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        mw.export_img_act = QAction(mw, triggered=mw.export_image)
        mw.export_sql_act = QAction(mw, triggered=mw.export_sql)
        mw.exit_act = QAction(mw, triggered=mw.close)
        mw.reset_zoom_act = QAction(mw, triggered=mw.reset_zoom)

        # 2. Undo
        mw.undo_act = mw.undo_stack.createUndoAction(mw, "")
        mw.undo_act.setShortcut(QKeySequence.Undo)

        # 3. Phím tắt chỉnh sửa - Thiết lập Context WidgetWithChildrenShortcut để không bị Canvas nuốt phím
        mw.select_all_act = QAction(mw, triggered=mw.select_all)
        mw.select_all_act.setShortcut(QKeySequence.SelectAll)
        mw.select_all_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        mw.delete_act = QAction(mw, triggered=mw.delete_selected)
        mw.delete_act.setShortcuts([QKeySequence.Delete, QKeySequence(Qt.Key.Key_Backspace)])
        mw.delete_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        mw.copy_act = QAction(mw, triggered=mw.copy_selected_entity)
        mw.copy_act.setShortcut(QKeySequence.Copy)
        mw.copy_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        mw.paste_act = QAction(mw, triggered=mw.paste_entity)
        mw.paste_act.setShortcut(QKeySequence.Paste)
        mw.paste_act.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)

        mw.toggle_simplified_act = QAction(mw, checkable=True)
        mw.toggle_simplified_act.setChecked(False)
        mw.toggle_simplified_act.triggered.connect(mw.toggle_simplified_view)

        mw.format_act = QAction(mw, triggered=mw.open_format_dialog)
        mw.reset_ui_act = QAction(mw, triggered=mw.reset_default_ui)

        mw.toggle_shortcuts_act = QAction(mw, checkable=True)
        mw.toggle_shortcuts_act.setChecked(False)
        mw.toggle_shortcuts_act.triggered.connect(mw.toggle_shortcut_mode)

        mw.toggle_auto_prefix_act = QAction(mw, checkable=True)
        mw.toggle_auto_prefix_act.setChecked(False)
        mw.toggle_auto_prefix_act.triggered.connect(mw.toggle_auto_prefix_mode)

        mw.toggle_dark_mode_act = QAction(mw, checkable=True)
        mw.toggle_dark_mode_act.setChecked(mw.dark_mode_enabled)
        mw.toggle_dark_mode_act.triggered.connect(mw.toggle_dark_mode)

        mw.toggle_simplified_act = QAction(mw, checkable=True)
        mw.toggle_simplified_act.setChecked(EntityItem.simplified_mode)
        mw.toggle_simplified_act.triggered.connect(mw.toggle_simplified_view)



        # Đăng ký phím tắt vào cả MainWindow VÀ CanvasView
        for act in [
            mw.undo_act, 
            mw.select_all_act, 
            mw.delete_act, 
            mw.copy_act, 
            mw.paste_act, 
            mw.save_act, 
            mw.save_as_act,
            mw.open_act,
            mw.new_act
        ]:
            mw.addAction(act)
            mw.view.addAction(act)

        self.retranslate_actions()

    def retranslate_actions(self):
        """Cập nhật lại Text hiển thị của toàn bộ QAction theo current_lang"""
        mw = self.mw
        # Lấy từ điển theo ngôn ngữ hiện tại, mặc định fallback về 'vi' nếu thiếu
        t = TRANSLATIONS.get(mw.current_lang, TRANSLATIONS.get("vi", {}))

        # --- Menu File ---
        mw.new_act.setText(t.get("act_new", "Tạo mô hình mới"))
        mw.open_act.setText(t.get("act_open", "Mở mô hình..."))
        mw.save_act.setText(t.get("act_save", "Lưu mô hình"))

        if hasattr(mw, 'save_as_act'):
            mw.save_as_act.setText(t.get("act_save_as", "Lưu dưới dạng..."))

        mw.export_img_act.setText(t.get("act_export_img", "Xuất hình ảnh..."))
        mw.export_sql_act.setText(t.get("act_export_sql", "Xuất SQL DDL..."))
        mw.exit_act.setText(t.get("act_exit", "Thoát"))

        # --- Menu Edit ---
        mw.undo_act.setText(t.get("act_undo", "Hoàn tác"))
        mw.copy_act.setText(t.get("act_copy", "Sao chép Thực thể"))
        mw.paste_act.setText(t.get("act_paste", "Dán Thực thể"))
        mw.delete_act.setText(t.get("act_delete", "Xóa đối tượng"))
        mw.select_all_act.setText(t.get("act_select_all", "Chọn tất cả"))

        # --- Menu View & Settings ---
        mw.reset_zoom_act.setText(t.get("act_reset_zoom", "Đặt lại thu phóng"))
        mw.toggle_simplified_act.setText(t.get("act_toggle_simplified", "Hiển thị thu gọn"))
        mw.format_act.setText(t.get("act_format", "Định dạng Font & Màu sắc..."))
        mw.reset_ui_act.setText(t.get("act_reset_ui", "Khôi phục giao diện mặc định"))
        mw.toggle_shortcuts_act.setText(
            t.get("act_toggle_shortcuts", "Bật phím tắt vẽ nhanh (E/R/Esc)")
        )
        mw.toggle_auto_prefix_act.setText(
            t.get("act_toggle_auto_prefix", "Tự động đặt tiền tố (UPPERCASE & Prefix)")
        )
        mw.toggle_dark_mode_act.setText(t.get("act_toggle_dark_mode", "Dark Mode"))