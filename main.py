import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')

import ctypes
import winreg
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QFontDatabase
from src.views.main_window import MainWindow

def register_file_association():
    """Đăng ký đuôi file .ccdm với hệ thống Windows để hiển thị icon file.ico"""
    if sys.platform != "win32":
        return

    try:
        # Đường dẫn file chạy .exe hoặc main.py hiện tại
        app_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        
        # Đường dẫn icon hiển thị cho các file dữ liệu .ccdm
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        file_icon_path = os.path.join(base_dir, "assets", "icons", "file.ico")

        # Key registry mở rộng .ccdm
        ext_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.ccdm")
        winreg.SetValue(ext_key, "", winreg.REG_SZ, "CCDM.ProjectFile")
        winreg.CloseKey(ext_key)

        # Key định nghĩa loại file
        file_type_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\CCDM.ProjectFile")
        winreg.SetValue(file_type_key, "", winreg.REG_SZ, "CCDM Data Modeler Project")
        
        # Đặt Icon hiển thị cho file .ccdm (Dùng file.ico)
        default_icon_key = winreg.CreateKey(file_type_key, "DefaultIcon")
        winreg.SetValue(default_icon_key, "", winreg.REG_SZ, f'"{file_icon_path}"')
        winreg.CloseKey(default_icon_key)

        # Đặt lệnh mở mặc định khi double-click file .ccdm
        command_key = winreg.CreateKey(file_type_key, r"shell\open\command")
        winreg.SetValue(command_key, "", winreg.REG_SZ, f'"{app_path}" "%1"')
        winreg.CloseKey(command_key)
        
        winreg.CloseKey(file_type_key)

        # Thông báo cho Windows Refresh lại Icon Cache
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0x0000, None, None)
    except Exception as e:
        print(f"[Warning] Không thể đăng ký file association: {e}")

def load_custom_fonts(base_dir):
    """Load toàn bộ phông chữ (.ttf, .otf) từ thư mục assets/fonts"""
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    
    if os.path.exists(fonts_dir):
        for font_file in os.listdir(fonts_dir):
            if font_file.lower().endswith((".ttf", ".otf")):
                font_path = os.path.join(fonts_dir, font_file)
                font_id = QFontDatabase.addApplicationFont(font_path)
                if font_id != -1:
                    font_families = QFontDatabase.applicationFontFamilies(font_id)
                    print(f"[Font Loaded] {font_file} -> Family Name: {font_families}")
                else:
                    print(f"[Warning] Không thể load font: {font_file}")
    else:
        print(f"[Warning] Thư mục fonts không tồn tại: {fonts_dir}")

def main():
    # 1. FIX ICON TASKBAR CHO WINDOWS
    if sys.platform == "win32":
        try:
            myappid = "mycompany.ccdm.datamodeler.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            # Tự động đăng ký đuôi file khi chạy ứng dụng
            register_file_association()
        except Exception as e:
            print(f"Warning: Could not set AppUserModelID/Association: {e}")

    app = QApplication(sys.argv)

    # 2. XÁC ĐỊNH ĐƯỜNG DẪN AN TOÀN CHO CẢ WINDOWS & LINUX
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    app_icon_path = os.path.join(base_dir, "assets", "icons", "CCDM.ico")

    # 3. NẠP PHÔNG CHỮ TỪ THƯ MỤC assets/fonts
    load_custom_fonts(base_dir)

    # 4. GÁN ICON CHO TOÀN BỘ ỨNG DỤNG (Dùng CCDM.ico cho App/Shortcut/Taskbar)
    if os.path.exists(app_icon_path):
        app.setWindowIcon(QIcon(app_icon_path))
    else:
        print(f"[Warning] Không tìm thấy file icon tại: {app_icon_path}")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()