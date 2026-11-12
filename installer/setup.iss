; Inno Setup script for Simple Converter. Build with installer\build.ps1.
#define AppName "Simple Converter"
#define AppVersion "1.1.0"
#define AppExe "SimpleConverter.exe"
#define AppUrl "https://github.com/Magnifico9/simple-converter"

[Setup]
AppId={{6E1F4C2A-7B3D-4E8A-9C51-2F7A6D0B8E43}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Haitham Joban
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE
SetupIconFile=..\assets\simple-converter.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
OutputDir=Output
OutputBaseFilename=SimpleConverter-Setup-{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=no

[Messages]
FinishedLabel=Setup has finished installing [name].%n%nRight-click any file and choose "Convert to" to use it.%nOn the compact Windows 11 menu, it is under "Show more options".

[Tasks]
Name: "libreoffice"; Description: "Install LibreOffice: needed for Word, Excel and PowerPoint files (free, about 350 MB download)"; Check: WingetAvailable and not LibreOfficeInstalled
Name: "calibre"; Description: "Install Calibre: needed for ebooks like EPUB and MOBI (free, about 200 MB download)"; Flags: unchecked; Check: WingetAvailable and not CalibreInstalled

[Files]
Source: "..\dist\SimpleConverter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"
Source: "..\README.md"; DestDir: "{app}"

[Run]
Filename: "{cmd}"; Parameters: "/c winget install --id TheDocumentFoundation.LibreOffice -e --silent --accept-package-agreements --accept-source-agreements"; StatusMsg: "Installing LibreOffice (this can take a few minutes)..."; Flags: runhidden waituntilterminated; Tasks: libreoffice
Filename: "{cmd}"; Parameters: "/c winget install --id calibre.calibre -e --silent --accept-package-agreements --accept-source-agreements"; StatusMsg: "Installing Calibre (this can take a few minutes)..."; Flags: runhidden waituntilterminated; Tasks: calibre
Filename: "{app}\{#AppExe}"; Parameters: "--register"; StatusMsg: "Adding the Convert to menu..."; Flags: runhidden waituntilterminated

[UninstallRun]
Filename: "{app}\{#AppExe}"; Parameters: "--unregister"; Flags: runhidden waituntilterminated; RunOnceId: "Unregister"

[Code]
function WingetAvailable: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Microsoft\WindowsApps\winget.exe'));
end;

function LibreOfficeInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\LibreOffice\program\soffice.exe')) or
            FileExists(ExpandConstant('{commonpf32}\LibreOffice\program\soffice.exe'));
end;

function CalibreInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{commonpf64}\Calibre2\ebook-convert.exe')) or
            FileExists(ExpandConstant('{commonpf32}\Calibre2\ebook-convert.exe'));
end;
