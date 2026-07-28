; Inno Setup Script f■r FerdlWorks
; UTF-8 mit BOM - Unicode unterst■tzt Umlaute
; Version wird von CI via /dMyAppVersion=X.X.X gesetzt

#define MyAppName "FerdlWorks"
#ifndef MyAppVersion
#define MyAppVersion "1.2.2"
#endif
#define MyAppVersionFull MyAppVersion + ".0"
#define MyAppPublisher "Sonderegger Software"
#define MyAppURL "https://github.com/soendi/FerdlWorks"
#define MyAppExeName "FerdlWorks.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVerName={#MyAppName} {#MyAppVersion}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersionFull}
VersionInfoDescription={#MyAppName}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=.
OutputBaseFilename={#MyAppName}-Setup
SetupIconFile=..\assets\ferdlworks.ico
UninstallDisplayIcon={app}\ferdlworks.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
AlwaysShowDirOnReadyPage=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\ferdlworks.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\data"; Permissions: users-modify

[Registry]
Root: HKLM; Subkey: "SOFTWARE\SondereggerSoftware\{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\SondereggerSoftware\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue
Root: HKLM; Subkey: "SOFTWARE\SondereggerSoftware\{#MyAppName}"; ValueType: string; ValueName: "UninstallPath"; ValueData: "{app}\unins000.exe"; Flags: uninsdeletevalue

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\ferdlworks.ico"
Name: "{group}\Deinstallieren"; Filename: "{app}\unins000.exe"; IconFilename: "{app}\ferdlworks.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\ferdlworks.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if MsgBox('M—chten Sie auch Ihre pers—nlichen Einstellungen (Registry) l—schen?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      RegDeleteKeyIncludingSubkeys(HKCU, 'SOFTWARE\SondereggerSoftware\FerdlWorks');
    end;
  end;
end;
