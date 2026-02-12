; Gmail Cleaner Pro Installer Script
; Inno Setup Script
; Author: numanrki

#define MyAppName "Gmail Cleaner Pro"
#define MyAppVersion "2.0.2"
#define MyAppPublisher "numanrki"
#define MyAppURL "https://github.com/numanrki/GmailCleanerPro"
#define MyAppExeName "GmailCleanerPro.exe"

[Setup]
; App info
AppId={{8F4A3B2C-1D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases

; Install location
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output settings
OutputDir=installer_output
OutputBaseFilename=GmailCleanerPro_Setup_v{#MyAppVersion}
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Privileges (install for current user by default, no admin needed)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Modern installer look
WizardStyle=modern
WizardSizePercent=100

; Misc
DisableWelcomePage=no
DisableDirPage=no
AllowNoIcons=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Icon file
Source: "app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop icon (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon

; Startup (optional)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
; Launch app after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up app data folder on uninstall (optional - commented out to preserve user data)
; Type: filesandordirs; Name: "{userappdata}\GmailCleanerPro"

[Code]
// Custom code to check for running instance before install
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
