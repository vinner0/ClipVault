@echo off
setlocal

echo ============================================
echo  ClipVault Build Script
echo ============================================
echo.

:: Stop any running instance so the old exe is not locked
echo Stopping any running ClipVault instance...
taskkill /f /im ClipVault.exe >nul 2>&1
echo Done.
echo.

:: Step 1: Install dependencies
echo [1/3] Installing / verifying dependencies...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See above for details.
    pause
    exit /b 1
)
echo.
echo Dependencies OK.
echo.

:: Step 2: Clean previous build artifacts
echo [2/3] Cleaning previous build artifacts...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist
if exist ClipVault.spec del /q ClipVault.spec
echo Done.
echo.

:: Step 3: Build with PyInstaller
echo [3/3] Running PyInstaller...
echo.
python -m PyInstaller ^
    --noconsole ^
    --onefile ^
    --name ClipVault ^
    --icon=assets\icon.png ^
    --add-data "assets;assets" ^
    --hidden-import=pynput.keyboard._win32 ^
    --hidden-import=pynput.mouse._win32 ^
    main.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller build failed. See above for details.
    pause
    exit /b 1
)

echo.

:: Step 4: Copy exe to local install dir (outside Dropbox) for reliable auto-startup
echo [4/4] Installing to %%LOCALAPPDATA%%\ClipVault\ ...
if not exist "%LOCALAPPDATA%\ClipVault" mkdir "%LOCALAPPDATA%\ClipVault"
copy /y "dist\ClipVault.exe" "%LOCALAPPDATA%\ClipVault\ClipVault.exe"
if errorlevel 1 (
    echo WARNING: Could not copy to local install dir. Auto-startup may not work.
) else (
    echo Installed: %LOCALAPPDATA%\ClipVault\ClipVault.exe
)

echo.
echo ============================================
echo  Build complete!
echo  Output: dist\ClipVault.exe
echo  Local:  %LOCALAPPDATA%\ClipVault\ClipVault.exe
echo ============================================
echo.
pause
