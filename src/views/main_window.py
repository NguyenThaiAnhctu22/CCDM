import faulthandler
faulthandler.enable()

import json
import uuid
import tempfile
import os
import sys

from PySide6.QtWidgets import (
    QMainWindow, QToolBar, QStatusBar, QFileDialog, 
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QDockWidget, QMessageBox
)
from PySide6.QtGui import QIcon, QFont, QColor, QUndoStack
from PySide6.QtCore import Qt, QSize, QSettings, QCoreApplication, QTimer
from PySide6.QtWidgets import QGraphicsItem

from .scene import DiagramScene
from .canvas_view import CanvasView
from .items.entity_item import EntityItem
from .items.relationship_item import RelationshipItem
from .actions_manager import ActionsManager

from ..models.project import Project
from ..models.entity import Entity
from ..models.attribute import Attribute

from ..controllers.serializer import Serializer
from ..controllers.exporter import Exporter

from ..helpers.icon_helper import create_entity_pixmap, create_relationship_pixmap
from .dialogs.format_dialog import FormatDialog, FormatStyle
from .dialogs.entity_dialog import EntityDialog
from .dialogs.relationship_dialog import RelationshipDialog
from ..commands.snapshot_command import SnapshotCommand
from ..helpers.translations import TRANSLATIONS
from ..helpers.theme_helper import apply_theme


class MainWindow(QMainWindow):
    APP_NAME = "CCDM"

    def __init__(self):
        super().__init__()
        self.resize(1300, 800)

        QCoreApplication.setOrganizationName("MyCompany")
        QCoreApplication.setApplicationName("DataModeler")

        # 1. KHỞI TẠO BIẾN TRẠNG THÁI & MODEL MẶC ĐỊNH
        self.current_lang = "en"  # Ngôn ngữ mặc định
        self.current_file_path = None
        self._is_dirty = False
        self.copied_entity_data = None
        self.auto_prefix_enabled = False
        self.dark_mode_enabled = False

        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(self._on_undo_clean_changed)

        self.project = Project()
        self.scene = DiagramScene(self)
        self.view = CanvasView(self.scene, self)
        self.setCentralWidget(self.view)

        self.setDockOptions(
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        self.global_styles = {
            "entity": FormatStyle(QFont("Readdex Pro", 13, QFont.Weight.Medium), QColor("#000000")),
            "attribute": FormatStyle(QFont("Readdex Pro", 13, QFont.Weight.Medium), QColor("#000000")),
            "relationship": FormatStyle(
                QFont("Readdex Pro", 12, QFont.Weight.Medium), QColor("#000000"),
                line_width=1, line_color=QColor("#1f5ca9")
            )
        }

        # 2. ĐỌC SETTINGS TRƯỚC (Để lấy self.current_lang từ lần dùng gần nhất)
        self.read_settings()

        # 3. KHỞI TẠO UI, ACTIONS, DOCKS & MENUS
        self.actions_mgr = ActionsManager(self)
        
        self._create_toolbox_dock()
        self._create_object_browser_dock()
        self._create_toolbar()
        self._create_menus()  # Lúc này _create_menus sẽ tạo menu dựa trên self.current_lang vừa đọc

        # 4. KẾT NỐI SIGNALS & EVENTS
        self.view.entity_requested.connect(self.create_entity_at_pos)
        self.view.relationship_requested.connect(self.create_relationship_between_entities)
        self.view.mode_changed.connect(self._on_mode_changed)

        # 5. RETRANSLATE VÀ CẬP NHẬT GIAO DIỆN LẦN CUỐI
        self.retranslate_ui()
        self.statusBar().showMessage("Sẵn sàng" if self.current_lang == "vi" else "Ready")

        # KHỞI TẠO AUTO-SAVE TIMER
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(120000)  # Chạy mỗi 2 phút (120,000 ms)
        self.autosave_timer.timeout.connect(self._do_auto_save)
        self.autosave_timer.start()
        # Kiểm tra file Auto-recovery khi vừa mở ứng dụng
        QTimer.singleShot(500, self._check_auto_recovery)  # Chạy sau 0.5s để UI khởi tạo xong

    def toggle_dark_mode(self, checked: bool):
        self.dark_mode_enabled = checked
        apply_theme(self, checked)

        msg = "Đã bật Chế độ tối" if checked else "Đã tắt Chế độ tối"
        self.statusBar().showMessage(msg, 3000)

    def _get_autosave_path(self) -> str:
        """Trả về đường dẫn file tự động khôi phục trong thư mục Temp của OS"""
        temp_dir = tempfile.gettempdir()
        return os.path.join(temp_dir, "ccdm_autosave_tmp.cdm")

    def _get_backup_path(self, file_path: str) -> str:
        """Tạo đường dẫn file .bak tương ứng với file chính"""
        return file_path + ".bak"

    def _do_auto_save(self):
        """Thực hiện lưu tạm trạng thái dự án ngầm ra thư mục temp của OS"""
        if not self.is_dirty:
            return

        try:
            autosave_file = self._get_autosave_path()
            Serializer.save_to_file(self.project, autosave_file)
            # Không thay đổi cờ self.is_dirty vì đây chỉ là bản sao lưu tạm
        except Exception as e:
            print(f"[Auto-save Error]: {e}")

    def _remove_autosave_file(self):
        """Xóa file temporary khi người dùng lưu file thành công hoặc đóng app an toàn"""
        autosave_file = self._get_autosave_path()
        if os.path.exists(autosave_file):
            try:
                os.remove(autosave_file)
            except OSError:
                pass

    def _check_auto_recovery(self):
        """Kiểm tra và hỏi người dùng có khôi phục dự án do lần crash trước đó không"""
        autosave_file = self._get_autosave_path()
        
        if os.path.exists(autosave_file):
            reply = QMessageBox.question(
                self,
                "Khôi phục dữ liệu (Auto-Recovery)",
                "Ứng dụng phát hiện có dữ liệu tạm do lần làm việc trước chưa được lưu hoặc bị tắt đột ngột.\n\n"
                "Bạn có muốn khôi phục lại dữ liệu này không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )

            if reply == QMessageBox.StandardButton.Yes:
                try:
                    with open(autosave_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._restore_state(content)
                    self.is_dirty = True
                    self.statusBar().showMessage("Đã khôi phục dữ liệu từ phiên làm việc trước!", 5000)
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi Khôi Phục", f"Không thể đọc file khôi phục:\n{str(e)}")
            
            # Xóa file temp sau khi người dùng đã lựa chọn (Đồng ý hoặc Từ chối)
            self._remove_autosave_file()

    # --- QUẢN LÝ TRẠNG THÁI LƯU & TIÊU ĐỀ CỬA SỔ ---

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @is_dirty.setter
    def is_dirty(self, value: bool):
        if self._is_dirty != value:
            self._is_dirty = value
            self.update_window_title()

    def update_window_title(self):
        """Cập nhật tên file và dấu * hiển thị trên Window Title"""
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        untitled_str = t.get("untitled", "Untitled")
        
        filename = os.path.basename(self.current_file_path) if self.current_file_path else untitled_str
        star = "*" if self.is_dirty else ""
        self.setWindowTitle(f"{filename}{star} - {self.APP_NAME}")

    def change_language(self, lang_code: str):
        """Thay đổi ngôn ngữ và re-translate lại UI"""
        if self.current_lang != lang_code:
            self.current_lang = lang_code
            self.retranslate_ui()
            self.statusBar().showMessage(
                "Đã chuyển sang Tiếng Việt" if lang_code == "vi" else "Switched to English", 3000
            )

    def retranslate_ui(self):
        """Cập nhật toàn bộ Text trên Menu, Actions, Docks, Toolbox, Browser theo current_lang"""
        # 1. Cập nhật các Action
        if hasattr(self, 'actions_mgr') and self.actions_mgr:
            self.actions_mgr.retranslate_actions()

        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])

        # 2. Cập nhật Menu Titles
        if hasattr(self, 'file_menu') and self.file_menu:
            self.file_menu.setTitle(t.get("menu_file", "File"))
        if hasattr(self, 'edit_menu') and self.edit_menu:
            self.edit_menu.setTitle(t.get("menu_edit", "Edit"))
        if hasattr(self, 'view_menu') and self.view_menu:
            self.view_menu.setTitle(t.get("menu_view", "View"))
        if hasattr(self, 'window_menu') and self.window_menu:
            self.window_menu.setTitle(t.get("menu_window", "Window"))
        if hasattr(self, 'lang_menu') and self.lang_menu:
            self.lang_menu.setTitle(t.get("menu_language", "Language"))

        # 3. Cập nhật Dock Titles
        if hasattr(self, 'toolbox_dock') and self.toolbox_dock:
            self.toolbox_dock.setWindowTitle(t.get("dock_toolbox", "Toolbox"))
        if hasattr(self, 'object_browser_dock') and self.object_browser_dock:
            self.object_browser_dock.setWindowTitle(t.get("dock_object_browser", "Object Browser"))

        # 4. Cập nhật Nội dung Items trong Toolbox
        if hasattr(self, 'toolbox_list') and self.toolbox_list:
            if hasattr(self, 'item_hdr_std'): self.item_hdr_std.setText(t.get("toolbox_sec_standard", "STANDARD"))
            if hasattr(self, 'item_pointer'): self.item_pointer.setText(t.get("toolbox_pointer", "  Pointer"))
            if hasattr(self, 'item_grabber'): self.item_grabber.setText(t.get("toolbox_grabber", "  Grabber"))
            if hasattr(self, 'item_hdr_erd'): self.item_hdr_erd.setText(t.get("toolbox_sec_erd", "ERD ELEMENTS"))
            if hasattr(self, 'item_entity'): self.item_entity.setText(t.get("toolbox_add_entity", " Add Entity"))
            if hasattr(self, 'item_rel'): self.item_rel.setText(t.get("toolbox_add_relation", " Add Relationship"))

        # 5. Cập nhật Header & Nội dung Object Browser
        if hasattr(self, 'tree_widget') and self.tree_widget:
            self.tree_widget.setHeaderLabels([
                t.get("browser_col_name", "Object Name"),
                t.get("browser_col_type", "Type")
            ])
            self.refresh_object_browser()

        # Đồng bộ trạng thái checkbox
        if hasattr(self, 'toggle_auto_prefix_act'):
            self.toggle_auto_prefix_act.setChecked(self.auto_prefix_enabled)
        
        if hasattr(self, 'toggle_shortcuts_act') and hasattr(self, 'view'):
            self.toggle_shortcuts_act.setChecked(self.view.shortcuts_enabled)

        if hasattr(self, 'toggle_simplified_act'):
            self.toggle_simplified_act.setChecked(EntityItem.simplified_mode)

        self.update_window_title()

    def _on_undo_clean_changed(self, is_clean: bool):
        """Kích hoạt khi UndoStack quay về/rời khỏi trạng thái đã Save"""
        self.is_dirty = not is_clean

    def maybe_save_changes(self) -> bool:
        """Hỏi lưu dự án nếu có thay đổi chưa lưu (Hỗ trợ Đa ngôn ngữ)"""
        if not self.is_dirty:
            return True

        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])
        untitled_str = t.get("untitled", "Untitled")
        filename = os.path.basename(self.current_file_path) if self.current_file_path else untitled_str

        # Tạo MessageBox đa ngôn ngữ
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(t.get("confirm_save_title", "Unsaved Changes"))
        msg_box.setText(t.get("confirm_save_msg", "Project '{}' has been modified.").format(filename))

        save_btn = msg_box.addButton(t.get("btn_save", "Save"), QMessageBox.AcceptRole)
        discard_btn = msg_box.addButton(t.get("btn_discard", "Don't Save"), QMessageBox.DestructiveRole)
        cancel_btn = msg_box.addButton(t.get("btn_cancel", "Cancel"), QMessageBox.RejectRole)

        msg_box.setDefaultButton(save_btn)
        msg_box.exec()

        clicked_btn = msg_box.clickedButton()

        if clicked_btn == save_btn:
            return self.save_project()
        elif clicked_btn == cancel_btn or clicked_btn is None:
            return False
        
        return True # Nút Discard được chọn

    # --- HÀM XỬ LÝ LƯU (SAVE & SAVE AS) ---

    def save_project(self) -> bool:
        """Thực hiện Save dự án"""
        if not self.current_file_path:
            return self.save_project_as()
        return self._do_save(self.current_file_path)

    def save_project_as(self) -> bool:
        """Thực hiện Save As dự án"""
        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Lưu dự án dưới dạng", 
            "", 
            "CCDM Project (*.ccdm);;JSON File (*.json);;All Files (*)"
        )
        if path:
            # Tự động thêm đuôi .ccdm nếu người dùng không gõ đuôi file
            if not os.path.splitext(path)[1]:
                path += ".ccdm"
            return self._do_save(path)
        return False

    def _do_save(self, path: str) -> bool:
        """Ghi dữ liệu xuống file, tạo bản sao lưu (.bak) và reset cờ Dirty"""
        try:
            # 1. TẠO FILE BACKUP (.bak) NẾU FILE CHÍNH ĐÃ TỒN TẠI
            if os.path.exists(path):
                backup_path = self._get_backup_path(path)
                try:
                    # Đổi tên file cũ thành file .bak (đè lên .bak cũ nếu có)
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(path, backup_path)
                except Exception as e:
                    print(f"[Warning] Không thể tạo file backup: {e}")

            # 2. GHI FILE CHÍNH MỚI
            Serializer.save_to_file(self.project, path)
            self.current_file_path = path
            self.undo_stack.setClean()
            self.update_window_title()

            # 3. DỌN DẸP FILE AUTOSAVE TẠM THỜI VÌ ĐÃ LƯU THÀNH CÔNG
            self._remove_autosave_file()

            self.statusBar().showMessage(f"Đã lưu dự án: {path}", 4000)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Lỗi Lưu File", f"Không thể lưu file dự án:\n{str(e)}")
            return False

    # --- HÀM QUẢN LÝ DỰ ÁN & ĐÓNG ỨNG DỤNG ---

    def new_project(self):
        if not self.maybe_save_changes():
            return

        self.scene.clear()
        self.project = Project()
        self.current_file_path = None
        self.undo_stack.clear()
        self.is_dirty = False
        self.update_window_title()
        self.refresh_object_browser()
        self.statusBar().showMessage("Đã tạo dự án mới", 3000)

    def open_project(self):
        if not self.maybe_save_changes():
            return

        path, _ = QFileDialog.getOpenFileName(
            self, 
            "Mở dự án", 
            "", 
            "CCDM Project (*.ccdm *.json);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._restore_state(content)
                self.current_file_path = path
                self.undo_stack.clear()
                self.undo_stack.setClean()  # Đánh dấu cờ is_dirty = False
                self.is_dirty = False
                self.update_window_title()
                
                # Tự động căn giữa sơ đồ sau khi mở
                if not self.scene.itemsBoundingRect().isEmpty():
                    self.view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

                self.statusBar().showMessage(f"Đã mở dự án: {path}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Mở File", f"Không thể đọc file dự án:\n{str(e)}")

    def closeEvent(self, event):
        if self.maybe_save_changes():
            self.write_settings()
            self._remove_autosave_file()
            event.accept()
        else:
            event.ignore()

    # --- KHỞI TẠO DOCK & MENUS ---

    def _create_toolbox_dock(self):
        """Khởi tạo Dock Toolbox và lưu lại các tham chiếu Item để retranslate_ui()"""
        self.toolbox_dock = QDockWidget("Toolbox", self)
        self.toolbox_dock.setObjectName("ToolboxDock")
        self.toolbox_list = QListWidget(self)
        self.toolbox_list.setIconSize(QSize(20, 20))

        font_bold = QFont()
        font_bold.setBold(True)

        # --- NHÓM STANDARD ---
        self.item_hdr_std = QListWidgetItem("STANDARD")
        self.item_hdr_std.setFlags(Qt.ItemFlag.NoItemFlags)
        self.item_hdr_std.setFont(font_bold)
        self.toolbox_list.addItem(self.item_hdr_std)

        self.item_pointer = QListWidgetItem("  Pointer (Chọn)")
        self.item_pointer.setData(Qt.ItemDataRole.UserRole, "POINTER")
        
        self.item_grabber = QListWidgetItem("  Grabber (Kéo Canvas)")
        self.item_grabber.setData(Qt.ItemDataRole.UserRole, "GRABBER")

        self.toolbox_list.addItem(self.item_pointer)
        self.toolbox_list.addItem(self.item_grabber)

        # --- NHÓM ERD ELEMENTS ---
        self.item_hdr_erd = QListWidgetItem("ERD ELEMENTS")
        self.item_hdr_erd.setFlags(Qt.ItemFlag.NoItemFlags)
        self.item_hdr_erd.setFont(font_bold)
        self.toolbox_list.addItem(self.item_hdr_erd)

        self.item_entity = QListWidgetItem(QIcon(create_entity_pixmap(20)), " Thêm Entity")
        self.item_entity.setData(Qt.ItemDataRole.UserRole, "ADD_ENTITY")

        self.item_rel = QListWidgetItem(QIcon(create_relationship_pixmap(20)), " Thêm Relationship")
        self.item_rel.setData(Qt.ItemDataRole.UserRole, "ADD_RELATIONSHIP")

        self.toolbox_list.addItem(self.item_entity)
        self.toolbox_list.addItem(self.item_rel)

        # Mặc định chọn Pointer
        self.toolbox_list.setCurrentItem(self.item_pointer)

        self.toolbox_list.itemClicked.connect(self._on_toolbox_clicked)
        self.toolbox_dock.setWidget(self.toolbox_list)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.toolbox_dock)

    def _create_object_browser_dock(self):
        self.object_browser_dock = QDockWidget("Object Browser", self)
        self.object_browser_dock.setObjectName("ObjectBrowserDock")
        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setHeaderLabels(["Tên đối tượng", "Loại"])
        self.tree_widget.setColumnWidth(0, 160)

        self.tree_widget.itemClicked.connect(self._on_object_browser_clicked)
        self.tree_widget.itemDoubleClicked.connect(self._on_object_browser_double_clicked)

        self.object_browser_dock.setWidget(self.tree_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.object_browser_dock)

    def _create_toolbar(self):
        self.main_toolbar = QToolBar("Main Toolbar")
        self.main_toolbar.setObjectName("MainToolBar")
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.main_toolbar)
        self.main_toolbar.addAction(self.new_act)
        self.main_toolbar.addAction(self.save_act)
        self.main_toolbar.addAction(self.undo_act)
        self.main_toolbar.addAction(self.reset_zoom_act)

    def _create_menus(self):
        menu_bar = self.menuBar()

        # 1. Khởi tạo menu rỗng và gán vào self để retranslate_ui() cập nhật được
        self.file_menu = menu_bar.addMenu("")
        self.file_menu.addAction(self.new_act)
        self.file_menu.addAction(self.open_act)
        self.file_menu.addAction(self.save_act)
        if hasattr(self, 'save_as_act'):
            self.file_menu.addAction(self.save_as_act)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_img_act)
        self.file_menu.addAction(self.export_sql_act)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_act)

        self.edit_menu = menu_bar.addMenu("")
        self.edit_menu.addAction(self.undo_act)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.copy_act)
        self.edit_menu.addAction(self.paste_act)
        self.edit_menu.addAction(self.delete_act)
        self.edit_menu.addAction(self.select_all_act)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.format_act)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.toggle_auto_prefix_act)

        self.view_menu = menu_bar.addMenu("")
        self.view_menu.addAction(self.reset_zoom_act)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.toggle_simplified_act)
        self.view_menu.addAction(self.toggle_dark_mode_act)

        self.window_menu = menu_bar.addMenu("")
        self.window_menu.addAction(self.toolbox_dock.toggleViewAction())
        self.window_menu.addAction(self.object_browser_dock.toggleViewAction())
        self.window_menu.addAction(self.main_toolbar.toggleViewAction())
        self.window_menu.addSeparator()
        self.window_menu.addAction(self.reset_ui_act)
        self.window_menu.addAction(self.toggle_shortcuts_act)

        # 2. Khởi tạo Menu Ngôn ngữ
        self.lang_menu = menu_bar.addMenu("")
        from PySide6.QtGui import QActionGroup, QAction
        
        self.lang_group = QActionGroup(self)
        self.lang_group.setExclusive(True)

        self.action_lang_vi = QAction("Tiếng Việt", self, checkable=True)
        self.action_lang_en = QAction("English", self, checkable=True)

        if self.current_lang == "vi":
            self.action_lang_vi.setChecked(True)
        else:
            self.action_lang_en.setChecked(True)

        self.action_lang_vi.triggered.connect(lambda: self.change_language("vi"))
        self.action_lang_en.triggered.connect(lambda: self.change_language("en"))

        self.lang_group.addAction(self.action_lang_vi)
        self.lang_group.addAction(self.action_lang_en)

        self.lang_menu.addAction(self.action_lang_vi)
        self.lang_menu.addAction(self.action_lang_en)

        # 3. Cập nhật lại toàn bộ Tiêu đề Menu & Action theo ngôn ngữ hiện tại
        self.retranslate_ui()

    def toggle_auto_prefix_mode(self, checked: bool):
        self.auto_prefix_enabled = checked
        msg = "Đã BẬT hỗ trợ đặt tên Entity/Attribute" if checked else "Đã TẮT hỗ trợ đặt tên"
        self.statusBar().showMessage(msg, 3000)

    # Khi mở EntityDialog (ở hàm xử lý double click hoặc edit item):
    def open_entity_dialog(self, entity_item):
        old_state = self._capture_state()
        dialog = EntityDialog(entity_item.entity, auto_prefix=self.auto_prefix_enabled, parent=self)
        if dialog.exec():
            entity_item.update_content()
            new_state = self._capture_state()
            self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Chỉnh sửa Entity"))

    def open_relationship_dialog(self, rel_item):
        """Mở RelationshipDialog để chỉnh sửa Relationship tương ứng (gọi từ Canvas hoặc Object Browser)"""
        old_state = self._capture_state()

        src_name = getattr(getattr(rel_item.source_item, 'entity', None), 'name', None) or getattr(rel_item.source_item, 'name', "Source Entity")
        tgt_name = getattr(getattr(rel_item.target_item, 'entity', None), 'name', None) or getattr(rel_item.target_item, 'name', "Target Entity")

        dialog = RelationshipDialog(rel_item.rel_model, src_name, tgt_name, rel_item=rel_item, parent=self)
        if dialog.exec():
            data = dialog.get_data()
            rel_item.rel_model.name = data["name"]
            rel_item.rel_model.source_cardinality = data["source_cardinality"]
            rel_item.rel_model.target_cardinality = data["target_cardinality"]
            rel_item.rel_model.is_dependent_source = data.get("is_dependent_source", False)
            rel_item.rel_model.is_dependent_target = data.get("is_dependent_target", False)

            if hasattr(rel_item, 'label_item') and rel_item.label_item:
                rel_item.label_item.setPlainText(data["name"])
            rel_item.update_position()

            new_state = self._capture_state()
            self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Chỉnh sửa Relationship"))
            self.refresh_object_browser()

    def toggle_shortcut_mode(self, checked: bool):
        """Kích hoạt hoặc hủy kích hoạt tính năng phím tắt vẽ nhanh"""
        self.view.shortcuts_enabled = checked
        status_msg = "Đã BẬT phím tắt vẽ nhanh (E: Entity, R: Relationship, Esc: Hủy)" if checked else "Đã TẮT phím tắt vẽ nhanh"
        self.statusBar().showMessage(status_msg, 3000)

    # --- SNAPSHOT & RESTORE ---

    def _capture_state(self) -> str:
        temp_fd, temp_path = tempfile.mkstemp(suffix=".json")
        os.close(temp_fd)
        Serializer.save_to_file(self.project, temp_path)
        with open(temp_path, "r", encoding="utf-8") as f:
            data_str = f.read()
        try: os.remove(temp_path)
        except OSError: pass
        return data_str

    def _restore_state(self, state_str: str):
        temp_fd, temp_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
            f.write(state_str)
        self.project = Serializer.load_from_file(temp_path)
        try: os.remove(temp_path)
        except OSError: pass

        if hasattr(self.project, 'styles') and self.project.styles:
            for k in ["entity", "attribute", "relationship"]:
                if k in self.project.styles:
                    self.global_styles[k] = FormatStyle.from_dict(self.project.styles[k])

        self.scene.clear()
        items_map = {}
        for entity in self.project.entities.values():
            item = EntityItem(entity)
            item.apply_style(self.global_styles["entity"], self.global_styles["attribute"])
            self.scene.addItem(item)
            items_map[entity.id] = item

        for rel_model in self.project.relationships:
            src_item = items_map.get(rel_model.source_id)
            tgt_item = items_map.get(rel_model.target_id)
            if src_item and tgt_item:
                rel_item = RelationshipItem(rel_model, src_item, tgt_item)
                rel_item.apply_style(self.global_styles["relationship"])
                self.scene.addItem(rel_item)

        self.view.update_all_relationships()
        self.refresh_object_browser()

    # --- ACTIONS XỬ LÝ PHÍM TẮT ---

    def select_all(self):
        """Ctrl + A"""
        for item in self.scene.items():
            if item.flags() & item.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)

    def delete_selected(self):
        selected_items = self.scene.selectedItems()
        if not selected_items:
            return

        old_state = self._capture_state()  # Lưu trạng thái trước khi xóa

        for item in selected_items:
            if isinstance(item, EntityItem):
                rels_to_remove = [r for r in self.project.relationships if r.source_id == item.entity.id or r.target_id == item.entity.id]
                for rel in rels_to_remove:
                    self.project.relationships.remove(rel)
                if item.entity.id in self.project.entities:
                    del self.project.entities[item.entity.id]
                self.scene.removeItem(item)
            elif isinstance(item, RelationshipItem):
                if item.rel_model in self.project.relationships:
                    self.project.relationships.remove(item.rel_model)
                self.scene.removeItem(item)

        new_state = self._capture_state()  # Lưu trạng thái sau khi xóa
        
        # Đẩy vào undo_stack thay vì clear()
        self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Xóa đối tượng"))
        
        self.view.update_all_relationships()
        self.refresh_object_browser()

    def copy_selected_entity(self):
        """Ctrl + C: Sao chép các Entity được chọn và tự động đính kèm Relationship nếu đủ Source & Target"""
        selected_items = self.scene.selectedItems()
        selected_entities = [item.entity for item in selected_items if isinstance(item, EntityItem)]

        if not selected_entities:
            return

        # Tập hợp các ID của Entity được chọn
        selected_entity_ids = {entity.id for entity in selected_entities}

        # Tìm các Relationship thỏa mãn: Cả Source và Target đều thuộc danh sách Entity được chọn
        copied_relationships = []
        for rel in self.project.relationships:
            if rel.source_id in selected_entity_ids and rel.target_id in selected_entity_ids:
                copied_relationships.append(rel.to_dict() if hasattr(rel, 'to_dict') else rel.__dict__)

        # Đóng gói dữ liệu clipboard
        clipboard_payload = {
            "entities": [entity.to_dict() for entity in selected_entities],
            "relationships": copied_relationships
        }

        self.copied_entity_data = json.dumps(clipboard_payload)
        self.statusBar().showMessage(
            f"Đã sao chép {len(selected_entities)} Entity và {len(copied_relationships)} Relationship."
        )

    def paste_entity(self):
        """Ctrl + V: Dán các Entity và Relationship đã sao chép ra vị trí mới và tự động chọn nhóm mới"""
        if not self.copied_entity_data:
            return

        old_state = self._capture_state()
        data = json.loads(self.copied_entity_data)

        raw_entities = data.get("entities", [])
        raw_relationships = data.get("relationships", [])

        if not raw_entities:
            return

        id_mapping = {}
        new_entity_ids = set()

        # 1. Tái tạo các Entity trong Model & Scene
        for e_data in raw_entities:
            old_id = e_data.get("id")
            new_entity = Entity.from_dict(e_data)
            
            new_id = str(uuid.uuid4())
            new_entity.id = new_id
            new_entity.name = f"{e_data.get('name', 'Entity')}_Copy"
            new_entity.x += 30
            new_entity.y += 30

            id_mapping[old_id] = new_id
            new_entity_ids.add(new_id)

            self.project.add_entity(new_entity)
            item = EntityItem(new_entity)
            item.apply_style(self.global_styles["entity"], self.global_styles["attribute"])
            self.scene.addItem(item)

        # 2. Tái tạo các Relationship
        for r_data in raw_relationships:
            old_src_id = r_data.get("source_id") or r_data.get("source_entity_id")
            old_tgt_id = r_data.get("target_id") or r_data.get("target_entity_id")

            if old_src_id in id_mapping and old_tgt_id in id_mapping:
                new_src_id = id_mapping[old_src_id]
                new_tgt_id = id_mapping[old_tgt_id]

                # Lấy các EntityItem mới vừa được tạo từ Scene
                items_map = {item.entity.id: item for item in self.scene.items() if isinstance(item, EntityItem)}
                src_item = items_map.get(new_src_id)
                tgt_item = items_map.get(new_tgt_id)

                if src_item and tgt_item:
                    rel_model = self.project.create_relationship(new_src_id, new_tgt_id)
                    
                    if "name" in r_data: rel_model.name = r_data["name"]
                    if "source_cardinality" in r_data: rel_model.source_cardinality = r_data["source_cardinality"]
                    if "target_cardinality" in r_data: rel_model.target_cardinality = r_data["target_cardinality"]
                    if "is_dependent_source" in r_data: rel_model.is_dependent_source = r_data["is_dependent_source"]
                    if "is_dependent_target" in r_data: rel_model.is_dependent_target = r_data["is_dependent_target"]

                    rel_item = RelationshipItem(rel_model, src_item, tgt_item)
                    rel_item.apply_style(self.global_styles["relationship"])
                    self.scene.addItem(rel_item)

        # 3. Đẩy Undo Snapshot (Lưu ý: Lệnh này sẽ gọi _restore_state() và TÁI TẠO LẠI TOÀN BỘ ITEM)
        new_state = self._capture_state()
        self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Dán đối tượng"))
        
        self.view.update_all_relationships()
        self.refresh_object_browser()

        # 4. CHỌN LẠI ĐỐI TƯỢNG BẰNG CÁCH QUAN SÁT SCENE MỚI (Tránh dùng Pointer C++ cũ đã bị delete)
        self.scene.clearSelection()

        for item in self.scene.items():
            if isinstance(item, EntityItem) and item.entity.id in new_entity_ids:
                item.setSelected(True)
            elif isinstance(item, RelationshipItem):
                if item.source_item.entity.id in new_entity_ids and item.target_item.entity.id in new_entity_ids:
                    item.setSelected(True)

        self.view.setFocus()

    def create_entity_at_pos(self, x: float, y: float):
        old_state = self._capture_state()
        count = len(self.project.entities) + 1
        entity = Entity(name=f"Entity_{count}", x=x, y=y)
        
        self.project.add_entity(entity)
        item = EntityItem(entity)
        item.apply_style(self.global_styles["entity"], self.global_styles["attribute"])
        self.scene.addItem(item)

        new_state = self._capture_state()
        self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Tạo Entity"))
        self.refresh_object_browser()

    def create_relationship_between_entities(self, source_id: str, target_id: str):
        old_state = self._capture_state()
        items_map = {item.entity.id: item for item in self.scene.items() if isinstance(item, EntityItem)}
        src_item, tgt_item = items_map.get(source_id), items_map.get(target_id)
        
        if src_item and tgt_item:
            rel_model = self.project.create_relationship(source_id, target_id)
            rel_item = RelationshipItem(rel_model, src_item, tgt_item)
            rel_item.apply_style(self.global_styles["relationship"])
            self.scene.addItem(rel_item)

            new_state = self._capture_state()
            self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Tạo Relationship"))
            self.view.update_all_relationships()
            self.refresh_object_browser()

    # --- BẢO TRÌ GIAO DIỆN & CẤU HÌNH ---

    def reset_default_ui(self):
        # 1. Khôi phục trạng thái hiển thị & vị trí các Dock, Toolbar
        self.toolbox_dock.show()
        self.object_browser_dock.show()
        self.main_toolbar.show()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.toolbox_dock)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.object_browser_dock)

        # 2. Lưu lại trạng thái Undo trước khi đổi định dạng
        old_state = self._capture_state()

        # 3. Tạo lại kiểu chữ & màu sắc mặc định gốc
        default_entity_font = QFont("Readex Pro", 13)
        default_entity_font.setStyleName("Deca Light")

        default_rel_font = QFont("Readex Pro", 12)
        default_rel_font.setStyleName("Deca Light")

        self.global_styles = {
            "entity": FormatStyle(default_entity_font, QColor("#000000")),
            "attribute": FormatStyle(QFont(default_entity_font), QColor("#000000")),
            "relationship": FormatStyle(
                default_rel_font, QColor("#000000"), line_width=1, line_color=QColor("#1f5ca9")
            )
        }

        # 4. Cập nhật vào Model của dự án hiện tại
        self.project.styles = {
            key: style.to_dict() for key, style in self.global_styles.items()
        }

        # 5. Áp dụng lên các đối tượng trên Scene & tạo lệnh Undo
        self._apply_global_styles()
        new_state = self._capture_state()
        self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Khôi phục giao diện mặc định"))

        self.statusBar().showMessage("Đã khôi phục giao diện, Font chữ và Màu sắc về mặc định!", 3000)

    def write_settings(self):
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.setValue("language", self.current_lang)
        settings.setValue("simplified_mode", EntityItem.simplified_mode)
        settings.setValue("dark_mode_enabled", self.dark_mode_enabled)
        settings.setValue("auto_prefix_enabled", self.auto_prefix_enabled)
        settings.setValue("shortcuts_enabled", getattr(self.view, "shortcuts_enabled", False))

    def read_settings(self):
        settings = QSettings()
        if settings.value("geometry"):
            self.restoreGeometry(settings.value("geometry"))
        if settings.value("windowState"):
            self.restoreState(settings.value("windowState"))

        # Đọc ngôn ngữ lưu trữ (mặc định là 'en' hoặc 'vi')
        self.current_lang = settings.value("language", "en")

        simplified = settings.value("simplified_mode", False, type=bool)
        EntityItem.simplified_mode = simplified

        self.dark_mode_enabled = settings.value("dark_mode_enabled", False, type=bool)
        if self.dark_mode_enabled:
            QTimer.singleShot(0, lambda: self.toggle_dark_mode(True))

        self.auto_prefix_enabled = settings.value("auto_prefix_enabled", False, type=bool)
        saved_shortcuts = settings.value("shortcuts_enabled", False, type=bool)
        
        # Gán lại trạng thái vào view
        if hasattr(self, 'view'):
            self.view.shortcuts_enabled = saved_shortcuts

        # Đọc styles mặc định của ứng dụng từ QSettings (fallback mặc định nếu file mới chưa có style riêng)
        default_entity_font = settings.value("default_styles/entity_font", QFont("Arial", 12))
        default_entity_color = QColor(settings.value("default_styles/entity_color", "#000000"))
        
        default_attr_font = settings.value("default_styles/attr_font", QFont("Arial", 12))
        default_attr_color = QColor(settings.value("default_styles/attr_color", "#000000"))

        default_rel_font = settings.value("default_styles/rel_font", QFont("Arial", 11))
        default_rel_color = QColor(settings.value("default_styles/rel_color", "#000000"))
        default_rel_line_width = settings.value("default_styles/rel_line_width", 1, type=int)
        default_rel_line_color = QColor(settings.value("default_styles/rel_line_color", "#06B423"))

        self.global_styles = {
            "entity": FormatStyle(default_entity_font, default_entity_color),
            "attribute": FormatStyle(default_attr_font, default_attr_color),
            "relationship": FormatStyle(
                default_rel_font, default_rel_color,
                default_rel_line_width, default_rel_line_color
            )
        }

    def open_format_dialog(self):
        dialog = FormatDialog(self.global_styles, self)
        if dialog.exec():
            old_state = self._capture_state()
            self.global_styles = dialog.get_styles()

            # 1. Lưu style vào model của file hiện tại (để khi lưu file .ccdm sẽ ăn theo file này)
            self.project.styles = {
                key: style.to_dict() for key, style in self.global_styles.items()
            }

            # 2. Nếu người dùng tick chọn "Lưu làm mặc định hệ thống"
            if dialog.is_save_as_default():
                settings = QSettings()
                settings.setValue("default_styles/entity_font", self.global_styles["entity"].font)
                settings.setValue("default_styles/entity_color", self.global_styles["entity"].color.name())
                settings.setValue("default_styles/attr_font", self.global_styles["attribute"].font)
                settings.setValue("default_styles/attr_color", self.global_styles["attribute"].color.name())
                settings.setValue("default_styles/rel_font", self.global_styles["relationship"].font)
                settings.setValue("default_styles/rel_color", self.global_styles["relationship"].color.name())
                settings.setValue("default_styles/rel_line_width", self.global_styles["relationship"].line_width)
                settings.setValue("default_styles/rel_line_color", self.global_styles["relationship"].line_color.name())
                self.statusBar().showMessage("Đã lưu làm định dạng mặc định cho các file sau!", 3000)

            # 3. Áp dụng lên Scene hiện tại & Tạo undo command
            self._apply_global_styles()
            new_state = self._capture_state()
            self.undo_stack.push(SnapshotCommand(self, old_state, new_state, "Đổi định dạng giao diện"))

    def _apply_global_styles(self):
        for item in self.scene.items():
            if isinstance(item, EntityItem):
                item.apply_style(self.global_styles["entity"], self.global_styles["attribute"])
            elif isinstance(item, RelationshipItem):
                item.apply_style(self.global_styles["relationship"])
        self.scene.update()

    def _on_toolbox_clicked(self, item: QListWidgetItem):
        mode = item.data(Qt.ItemDataRole.UserRole)
        if mode:
            self.view.set_mode(mode)

    def _on_object_browser_clicked(self, item: QTreeWidgetItem, column: int):
        """Xử lý Click đơn: Chọn đối tượng tương ứng trên Canvas"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        target_id = None
        if data["type"] in ["ENTITY", "RELATIONSHIP"]:
            target_id = data["id"]
        elif data["type"] == "ATTRIBUTE":
            target_id = data["entity_id"]  # Click vào Attribute thì chọn Entity chứa nó

        if not target_id:
            return

        # Bỏ chọn tất cả các item hiện tại trên Canvas
        self.scene.clearSelection()

        # Tìm item tương ứng trên Scene để highlight selection
        for canvas_item in self.scene.items():
            if isinstance(canvas_item, EntityItem) and canvas_item.entity.id == target_id:
                canvas_item.setSelected(True)
                self.view.centerOn(canvas_item)  # Căn giữa màn hình vào Entity được chọn
                break
            elif isinstance(canvas_item, RelationshipItem) and canvas_item.rel_model.id == target_id:
                canvas_item.setSelected(True)
                self.view.centerOn(canvas_item)  # Căn giữa màn hình vào Relationship được chọn
                break

    def _on_object_browser_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Xử lý Click đúp: Mở Dialog chỉnh sửa tương ứng (EntityDialog hoặc RelationshipDialog)"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        target_id = data.get("id")
        if data["type"] == "ATTRIBUTE":
            target_id = data.get("entity_id")

        # 1. Trường hợp Click đúp vào Entity (hoặc Attribute của nó)
        if data["type"] in ["ENTITY", "ATTRIBUTE"]:
            for canvas_item in self.scene.items():
                if isinstance(canvas_item, EntityItem) and canvas_item.entity.id == target_id:
                    self.open_entity_dialog(canvas_item)
                    break

        # 2. Trường hợp Click đúp vào Relationship
        elif data["type"] == "RELATIONSHIP":
            for canvas_item in self.scene.items():
                if isinstance(canvas_item, RelationshipItem) and canvas_item.rel_model.id == target_id:
                    self.open_relationship_dialog(canvas_item)
                    break

    def refresh_object_browser(self):
        """Cập nhật lại danh sách đối tượng trong Object Browser theo ngôn ngữ hiện tại"""
        self.tree_widget.clear()
        t = TRANSLATIONS.get(self.current_lang, TRANSLATIONS["en"])

        group_label = t.get("browser_node_group", "Group")
        
        # 1. Nhóm Entities
        entities_node = QTreeWidgetItem(self.tree_widget, [t.get("browser_group_entities", "Entities"), group_label])
        for entity in self.project.entities.values():
            e_node = QTreeWidgetItem(entities_node, [entity.name, "Entity"])
            # Lưu loại đối tượng và ID vào UserRole
            e_node.setData(0, Qt.ItemDataRole.UserRole, {"type": "ENTITY", "id": entity.id})
            
            for attr in entity.attributes:
                attr_node = QTreeWidgetItem(e_node, [attr.name, attr.data_type])
                # Attribute thuộc về Entity cha, truyền thêm parent_id để chọn Entity chứa nó
                attr_id = getattr(attr, 'id', attr.name)
                attr_node.setData(0, Qt.ItemDataRole.UserRole, {"type": "ATTRIBUTE", "id": attr_id, "entity_id": entity.id})

        # 2. Nhóm Relationships
        rels_node = QTreeWidgetItem(self.tree_widget, [t.get("browser_group_relations", "Relationships"), group_label])
        for rel in self.project.relationships:
            # Hiển thị tên (nếu có) hoặc ID của Relationship
            rel_display_name = rel.name if getattr(rel, 'name', None) else rel.id
            r_node = QTreeWidgetItem(rels_node, [rel_display_name, "Relationship"])
            r_node.setData(0, Qt.ItemDataRole.UserRole, {"type": "RELATIONSHIP", "id": rel.id})

        self.tree_widget.expandAll()

    def reset_zoom(self): self.view.resetTransform()

    def export_image(self):
        if self.scene.itemsBoundingRect().isEmpty():
            QMessageBox.warning(self, "Cảnh báo", "Sơ đồ trống, không có dữ liệu để xuất hình ảnh!")
            return

        # Đã cập nhật thứ tự lọc ưu tiên: PNG -> JPG -> EMF -> SVG
        path, selected_filter = QFileDialog.getSaveFileName(
            self, 
            "Xuất hình ảnh sơ đồ", 
            "CDM", 
            "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;EMF Windows Vector (*.emf);;SVG Vector Image (*.svg)"
        )
        
        if path:
            # Tự động gắn đuôi file theo option người dùng đang chọn trên FileDialog nếu thiếu extension
            if "png" in selected_filter.lower() and not path.lower().endswith(".png"):
                path += ".png"
            elif ("jpg" in selected_filter.lower() or "jpeg" in selected_filter.lower()) and not (path.lower().endswith(".jpg") or path.lower().endswith(".jpeg")):
                path += ".jpg"
            elif "emf" in selected_filter.lower() and not path.lower().endswith(".emf"):
                path += ".emf"
            elif "svg" in selected_filter.lower() and not path.lower().endswith(".svg"):
                path += ".svg"

            # Hộp thoại chọn kiểu xuất nền
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Tùy chọn nền xuất ảnh")
            msg_box.setText("Bạn muốn xuất ảnh kiểu nào?")
            
            btn_white = msg_box.addButton("Nền trắng tinh", QMessageBox.ButtonRole.AcceptRole)
            btn_grid = msg_box.addButton("Giữ nguyên ô lưới Canvas", QMessageBox.ButtonRole.ActionRole)
            btn_cancel = msg_box.addButton("Hủy", QMessageBox.ButtonRole.RejectRole)
            
            msg_box.exec()
            
            clicked_btn = msg_box.clickedButton()
            
            if clicked_btn == btn_cancel or clicked_btn is None:
                return

            is_white = (clicked_btn == btn_white)

            success = Exporter.export_to_image(self.scene, path, white_background=is_white)
            
            if success:
                self.statusBar().showMessage(f"Đã xuất hình ảnh: {path}", 4000)
            else:
                QMessageBox.critical(self, "Lỗi", "Không thể xuất file hình ảnh!")

    def export_sql(self):
        if not self.project.entities:
            QMessageBox.warning(self, "Cảnh báo", "Dự án chưa có Entity nào để tạo SQL DDL!")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 
            "Xuất câu lệnh SQL DDL", 
            "preliminary-database.sql", 
            "SQL File (*.sql);;All Files (*)"
        )
        
        if path:
            if not path.lower().endswith(".sql"):
                path += ".sql"

            try:
                sql_content = Exporter.generate_sql_ddl(self.project)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(sql_content)
                self.statusBar().showMessage(f"Đã xuất SQL DDL: {path}", 4000)
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Xuất SQL", f"Không thể tạo file SQL DDL:\n{str(e)}")

    def _on_mode_changed(self, mode: str):
        # Đồng bộ lựa chọn item hiển thị trên Toolbox khi mode thay đổi từ bên ngoài (như bấm chuột phải)
        for i in range(self.toolbox_list.count()):
            item = self.toolbox_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == mode:
                self.toolbox_list.setCurrentItem(item)
                break

    def toggle_simplified_view(self, checked: bool):
        EntityItem.simplified_mode = checked
        for item in self.scene.items():
            if isinstance(item, EntityItem): item.update_content()
        self.view.update_all_relationships()
        self.scene.update()