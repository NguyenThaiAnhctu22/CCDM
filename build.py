# Cài đặt PyInstaller
pip install pyinstaller

# Câu lệnh đóng gói trên Windows/Linux
pyinstaller --noconfirm --onedir --windowed --icon="assets/icons/CCDM.ico" --add-data "assets/icons;assets/icons" --name "CCDM" main.py