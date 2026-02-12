; Gmail Cleaner Pro Installer Script
; NSIS Modern User Interface

!include "MUI2.nsh"

; General
Name "Gmail Cleaner Pro"
OutFile "installer_output\GmailCleanerPro_Setup_v2.0.4.exe"
InstallDir "$PROGRAMFILES\GmailCleanerPro"
InstallDirRegKey HKLM "Software\GmailCleanerPro" "InstallDir"
RequestExecutionLevel admin

; Version info
VIProductVersion "2.0.4.0"
VIAddVersionKey "ProductName" "Gmail Cleaner Pro"
VIAddVersionKey "CompanyName" "numanrki"
VIAddVersionKey "FileDescription" "Gmail Cleaner Pro Installer"
VIAddVersionKey "FileVersion" "2.0.4"
VIAddVersionKey "ProductVersion" "2.0.4"
VIAddVersionKey "LegalCopyright" "© 2026 numanrki"

; Interface Settings
!define MUI_ABORTWARNING
!define MUI_ICON "app.ico"
!define MUI_UNICON "app.ico"

; Installer Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Language
!insertmacro MUI_LANGUAGE "English"

; Installer Section
Section "Install" SecInstall
    SetOutPath "$INSTDIR"
    
    ; Install main executable
    File "dist\GmailCleanerPro.exe"
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\Gmail Cleaner Pro"
    CreateShortcut "$SMPROGRAMS\Gmail Cleaner Pro\Gmail Cleaner Pro.lnk" "$INSTDIR\GmailCleanerPro.exe"
    CreateShortcut "$SMPROGRAMS\Gmail Cleaner Pro\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    
    ; Create Desktop shortcut
    CreateShortcut "$DESKTOP\Gmail Cleaner Pro.lnk" "$INSTDIR\GmailCleanerPro.exe"
    
    ; Store installation folder
    WriteRegStr HKLM "Software\GmailCleanerPro" "InstallDir" "$INSTDIR"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"
    
    ; Add to Add/Remove Programs
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "DisplayName" "Gmail Cleaner Pro"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "UninstallString" "$INSTDIR\Uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "DisplayIcon" "$INSTDIR\GmailCleanerPro.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "Publisher" "numanrki"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "DisplayVersion" "2.0.4"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro" "NoRepair" 1
SectionEnd

; Uninstaller Section
Section "Uninstall"
    ; Remove files
    Delete "$INSTDIR\GmailCleanerPro.exe"
    Delete "$INSTDIR\Uninstall.exe"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\Gmail Cleaner Pro\Gmail Cleaner Pro.lnk"
    Delete "$SMPROGRAMS\Gmail Cleaner Pro\Uninstall.lnk"
    RMDir "$SMPROGRAMS\Gmail Cleaner Pro"
    Delete "$DESKTOP\Gmail Cleaner Pro.lnk"
    
    ; Remove installation directory
    RMDir "$INSTDIR"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\GmailCleanerPro"
    DeleteRegKey HKLM "Software\GmailCleanerPro"
SectionEnd
