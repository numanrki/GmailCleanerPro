@echo off
echo ========================================
echo    Gmail Cleaner Pro - Build Script
echo    Author: @numanrki
echo ========================================
echo.

echo [1/4] Installing PyInstaller...
pip install pyinstaller -q

echo [2/4] Cleaning previous build...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul

echo [3/4] Building optimized executable...
python -m PyInstaller GmailCleanerPro.spec --noconfirm

echo [4/4] Done!
echo.
echo ========================================
echo    BUILD SUCCESSFUL!
echo ========================================
echo.
echo Your executable is ready:
echo    dist\GmailCleanerPro.exe
echo.
echo Next steps:
echo    1. Upload to GitHub Releases
echo    2. Share the .exe with anyone!
echo.
echo GitHub: https://github.com/numanrki
echo ========================================
pause
