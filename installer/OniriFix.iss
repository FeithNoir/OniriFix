; Instalador de OniriFix para Windows.
; Requiere Inno Setup 6: https://jrsoftware.org/isinfo.php
;
; Compilar desde la raíz del proyecto:
;   .\scripts\build_release.ps1
; o directamente:
;   iscc.exe installer\OniriFix.iss

#define AppName "OniriFix"
#define AppVersion "0.1.0"
#define AppPublisher "OniriFix contributors"
#define AppExeName "OniriFix.exe"
#define ProjectRoot ".."

[Setup]
AppId={{8D2B9F3A-4C71-4B8E-9E2A-6F1C5D7A0B42}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL=https://github.com/onirifix/onirifix
AppSupportURL=https://github.com/onirifix/onirifix/issues
AppUpdatesURL=https://github.com/onirifix/onirifix/releases
DefaultDirName={autopf}\OniriFix
DefaultGroupName=OniriFix
DisableProgramGroupPage=yes
LicenseFile={#ProjectRoot}\LICENSE
OutputDir={#ProjectRoot}\dist
OutputBaseFilename=OniriFix-Setup-{#AppVersion}
SetupIconFile={#ProjectRoot}\src\onirifix\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesEnvironment=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion=0.1.0.0
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Instalador de OniriFix
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "addtopath"; Description: "Añadir OniriFix al PATH del usuario"; GroupDescription: "Integración con el sistema:"; Flags: checkedonce
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: unchecked

[Files]
Source: "{#ProjectRoot}\dist\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\installer\onirifix-shell.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\config\reglas.yaml"; DestDir: "{app}\config"; Flags: ignoreversion
Source: "{#ProjectRoot}\examples\*"; DestDir: "{app}\examples"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ProjectRoot}\docs\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "{#ProjectRoot}\docs\files\*.md"; DestDir: "{app}\docs\files"; Flags: ignoreversion
Source: "{#ProjectRoot}\docs\screenshots\*.png"; DestDir: "{app}\docs\screenshots"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#ProjectRoot}\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\CONTRIBUTING.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\.env.template"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\OniriFix"; Filename: "{app}\onirifix-shell.cmd"; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\{#AppExeName}"; Comment: "Abrir OniriFix en una terminal"
Name: "{group}\Carpeta de OniriFix"; Filename: "{app}"; Comment: "Abrir la carpeta de instalación"
Name: "{group}\Desinstalar OniriFix"; Filename: "{uninstallexe}"
Name: "{autodesktop}\OniriFix"; Filename: "{app}\onirifix-shell.cmd"; WorkingDir: "%USERPROFILE%"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\onirifix-shell.cmd"; Description: "Abrir OniriFix"; Flags: nowait postinstall skipifsilent

[Registry]
Root: HKA; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  Path: string;
begin
  if not RegQueryStringValue(HKA, 'Environment', 'Path', Path) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + Uppercase(Param) + ';', ';' + Uppercase(Path) + ';') = 0;
end;

function RemovePathEntry(const Path, Entry: string): string;
var
  Rest, Part: string;
  P: Integer;
begin
  Result := '';
  Rest := Path;
  while Rest <> '' do
  begin
    P := Pos(';', Rest);
    if P = 0 then
    begin
      Part := Rest;
      Rest := '';
    end
    else
    begin
      Part := Copy(Rest, 1, P - 1);
      Rest := Copy(Rest, P + 1, Length(Rest));
    end;
    if (Part <> '') and (CompareText(Trim(Part), Entry) <> 0) then
    begin
      if Result <> '' then
        Result := Result + ';';
      Result := Result + Part;
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Path, NewPath: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    if RegQueryStringValue(HKA, 'Environment', 'Path', Path) then
    begin
      NewPath := RemovePathEntry(Path, ExpandConstant('{app}'));
      if NewPath <> Path then
        RegWriteExpandStringValue(HKA, 'Environment', 'Path', NewPath);
    end;
  end;
end;
