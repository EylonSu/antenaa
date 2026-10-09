; Inno Setup script for Antenna Tracker.
; Build: iscc /DAppVersion=0.1.0 installer\windows\setup.iss
; Expects the PyInstaller output in dist\AntennaTracker and drivers in installer\windows\drivers.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppName "antenaa"
#define AppExe "AntennaTracker.exe"

[Setup]
AppId={{7C4E2B6A-3F1D-4C8E-9A51-2D7B0E6F4A13}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Antenaa
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=AntennaTracker-{#AppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExe}

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "drivers"; Description: "Install USB serial drivers (CH340/CH341 and FTDI) for clone Arduino boards"; GroupDescription: "Drivers:"

[Files]
Source: "..\..\dist\AntennaTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "drivers\CH341SER\*"; DestDir: "{tmp}\drivers\CH341SER"; Flags: recursesubdirs createallsubdirs deleteafterinstall skipifsourcedoesntexist; Tasks: drivers
Source: "drivers\FTDI\*"; DestDir: "{tmp}\drivers\FTDI"; Flags: recursesubdirs createallsubdirs deleteafterinstall skipifsourcedoesntexist; Tasks: drivers

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; pnputil lives in System32; {sys} resolves to the native 64-bit dir in 64-bit install mode.
Filename: "{sys}\pnputil.exe"; Parameters: "/add-driver ""{tmp}\drivers\CH341SER\CH341SER.INF"" /install"; Flags: runhidden waituntilterminated; StatusMsg: "Installing CH340/CH341 driver..."; Tasks: drivers; Check: FileExists(ExpandConstant('{tmp}\drivers\CH341SER\CH341SER.INF'))
Filename: "{sys}\pnputil.exe"; Parameters: "/add-driver ""{tmp}\drivers\FTDI\*.inf"" /subdirs /install"; Flags: runhidden waituntilterminated; StatusMsg: "Installing FTDI driver..."; Tasks: drivers; Check: DirExists(ExpandConstant('{tmp}\drivers\FTDI'))
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
