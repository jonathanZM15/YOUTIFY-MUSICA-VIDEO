#define MyAppName "Youtify"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "jonathanZM15"
#define MyAppExeName "Youtify.exe"

[Setup]
AppId={{E3C6F949-4A6F-4D95-9B8F-4A4D7F4C4B39}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Youtify
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=Youtify-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible

[Files]
Source: "dist\Youtify.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Youtify"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Youtify"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Youtify"; Flags: nowait postinstall skipifsilent
