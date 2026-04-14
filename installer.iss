; VideoCat — Inno Setup installer script
; Builds: dist\VideoCat_Setup.exe

#define AppName "VideoCat"
#define AppVersion "1.0.0"
#define AppPublisher "hiyabh"
#define AppURL "https://github.com/hiyabh/video-cat"
#define AppExeName "VideoCat.exe"

[Setup]
AppId={{8A3F5B2E-4C9D-4E8F-9A1B-5F7D3E9C2B1A}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=VideoCat_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main app bundle from PyInstaller
Source: "dist\VideoCat\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Example env
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion
; README
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to install Ollama if not present
Filename: "https://ollama.com/download/OllamaSetup.exe"; Description: "Install Ollama (required for local AI — free)"; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\output"
Type: filesandordirs; Name: "{userappdata}\VideoCat"
