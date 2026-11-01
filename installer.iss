#define MyAppName "Youtify"
#include "build\version.iss"
#define MyAppPublisher "jonathanZM15"
#define MyAppExeName "Youtify.exe"

[Setup]
AppId={{E3C6F949-4A6F-4D95-9B8F-4A4D7F4C4B39}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/jonathanZM15/YOUTIFY-MUSICA-VIDEO
DefaultDirName={autopf}\Youtify
DefaultGroupName=Youtify
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UsePreviousPrivileges=yes
UsePreviousAppDir=yes
OutputDir=installer
OutputBaseFilename=Youtify-Setup
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Youtify.exe
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
LicenseFile=LICENSE

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "dist\Youtify\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Youtify"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Youtify"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Youtify"; Flags: nowait postinstall skipifsilent
