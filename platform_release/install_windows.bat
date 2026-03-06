@echo off
setlocal
echo ════════════════════════════════════════════════════════════
echo   ⚔  Katana Windows Auto-Installer  ⚔
echo ════════════════════════════════════════════════════════════

where git >nul 2>&1 || (echo ▸ Installing Git... && winget install --id Git.Git -e --source winget)
where python >nul 2>&1 || (echo ▸ Installing Python... && winget install --id Python.Python.3.12 -e --source winget)

set PATH=%PATH%;%USERPROFILE%\AppData\Local\Programs\Python\Python312\;%USERPROFILE%\AppData\Local\Programs\Python\Python312\Scripts\

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
