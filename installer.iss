[Setup]
AppName=CCDM
AppVersion=1.0
AppPublisher=NTA
DefaultDirName={autopf}\CCDM
DefaultGroupName=CCDM
UninstallDisplayIcon={app}\CCDM.exe
OutputDir="D:\Workspace\Project_C_PyQt\ProjectC\output"
OutputBaseFilename=CCDM_Setup
SetupIconFile="D:\Workspace\Project_C_PyQt\ProjectC\assets\icons\CCDM.ico"
Compression=lzma
SolidCompression=yes
ChangesAssociations=yes

; Trỏ thẳng đến file LICENSE không đuôi từ GitHub
LicenseFile="D:\Workspace\Project_C_PyQt\ProjectC\LICENSE"

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng trên màn hình (Desktop)"; GroupDescription: "Lựa chọn thêm:"
Name: "fileassoc"; Description: "Tự động gắn đuôi file .ccdm với CCDM Data Modeler"; GroupDescription: "Liên kết file:"

[Files]
; Bọc ngoặc kép cho đường dẫn chứa file build
Source: "D:\Workspace\Project_C_PyQt\ProjectC\dist\CCDM\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\CCDM Data Modeler"; Filename: "{app}\CCDM.exe"
Name: "{autodesktop}\CCDM Data Modeler"; Filename: "{app}\CCDM.exe"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: ".ccdm"; ValueType: string; ValueName: ""; ValueData: "CCDMProjectFile"; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCR; Subkey: "CCDMProjectFile"; ValueType: string; ValueName: ""; ValueData: "CCDM Data Modeler Project"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCR; Subkey: "CCDMProjectFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\icons\CCDM.ico"; Tasks: fileassoc
Root: HKCR; Subkey: "CCDMProjectFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\CCDM.exe"" ""%1"""; Tasks: fileassoc