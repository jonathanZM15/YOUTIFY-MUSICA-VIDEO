#define MyAppName "Youtify"
#define MyAppVersion "1.0.5"
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
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon-v105.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Files]
Source: "dist\Youtify.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon-v105.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\*"; DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

[Icons]
Name: "{autoprograms}\Youtify"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon-v105.ico"; IconIndex: 0
Name: "{autodesktop}\Youtify"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon-v105.ico"; IconIndex: 0

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Youtify"; Flags: nowait postinstall skipifsilent
