@echo off
setlocal
echo ════════════════════════════════════════════════════════════
echo   ⚔  Katana Windows Auto-Installer  ⚔
echo ════════════════════════════════════════════════════════════

where git >nul 2>&1 || (echo ▸ Installing Git... && winget install --id Git.Git -e --source winget)
where python >nul 2>&1 || (echo ▸ Installing Python... && winget install --id Python.Python.3.12 -e --source winget)
where cmake >nul 2>&1 || (echo ▸ Installing CMake... && winget install --id Kitware.CMake -e --source winget)
where ninja >nul 2>&1 || (echo ▸ Installing Ninja... && winget install --id Ninja-build.Ninja -e --source winget)
where cl >nul 2>&1 || (
    echo ▸ Installing Visual Studio Build Tools (C++ toolchain)...
    winget install --id Microsoft.VisualStudio.2022.BuildTools -e --source winget ^
        --override "--add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --passive --norestart"
)

echo ▸ Installing Print3r dependencies...
where perl >nul 2>&1 || (echo ▸ Installing Perl... && winget install --id StrawberryPerl.StrawberryPerl -e --source winget)
where openscad >nul 2>&1 || (echo ▸ Installing OpenSCAD... && winget install --id OpenSCAD.OpenSCAD -e --source winget)

REM Install CuraEngine standalone (not full Cura)
echo ▸ Installing CuraEngine from source (standalone slicer)...
call "%~dp0install_curaengine_windows.bat"
if errorlevel 1 (
    echo ✗ CuraEngine build failed.
    pause
    exit /b 1
)

set PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\;%ProgramFiles%\OpenSCAD\;%ProgramFiles%\StrawberryPerl\perl\bin\;%ProgramFiles%\StrawberryPerl\c\bin\;%ProgramFiles%\CMake\bin\;%ProgramFiles%\Ninja\

REM Create and enter Katana directory
set INSTALL_DIR=%USERPROFILE%\Katana
echo ▸ Creating install directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
cd /d "%INSTALL_DIR%"

echo ▸ Downloading Katana installer...
curl -LO https://raw.githubusercontent.com/JohnnyTech-PRINTR-Cyan/Katana/main/install.py

if exist install.py (
    echo ▸ Launching Katana installer...
    python install.py
) else (
    echo ✗ Failed to download install.py.
    pause
    exit /b 1
)
pause
