@echo off
setlocal
echo ════════════════════════════════════════════════════════════
echo   ⚔  Katana Windows Auto-Installer  ⚔
echo ════════════════════════════════════════════════════════════

where git >nul 2>&1 || (echo ▸ Installing Git... && winget install --id Git.Git -e --source winget)
where python >nul 2>&1 || (echo ▸ Installing Python... && winget install --id Python.Python.3.12 -e --source winget)

echo ▸ Installing Print3r dependencies...
where perl >nul 2>&1 || (echo ▸ Installing Perl... && winget install --id StrawberryPerl.StrawberryPerl -e --source winget)
where openscad >nul 2>&1 || (echo ▸ Installing OpenSCAD... && winget install --id OpenSCAD.OpenSCAD -e --source winget)

REM Install CuraEngine standalone (not full Cura)
echo ▸ Installing CuraEngine (standalone slicer)...
where CuraEngine >nul 2>&1 || (
    echo Note: CuraEngine standalone may need manual download from:
    echo   https://github.com/Ultimaker/CuraEngine/releases
    echo   Or install from MSYS2: pacman -S curaengine
)

set PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\;%ProgramFiles%\OpenSCAD\;%ProgramFiles%\StrawberryPerl\perl\bin\;%ProgramFiles%\StrawberryPerl\c\bin\

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
