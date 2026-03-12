@echo off
setlocal enabledelayedexpansion

echo Installing CuraEngine for Windows...

REM Define target directory
set "INSTALL_DIR=%USERPROFILE%\Katana\bin"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Check if already installed
if exist "%INSTALL_DIR%\CuraEngine.exe" (
    echo CuraEngine already installed at %INSTALL_DIR%\CuraEngine.exe
    "%INSTALL_DIR%\CuraEngine.exe" --version
    goto :eof
)

echo Downloading CuraEngine binary...

REM Use PowerShell to fetch the latest release tag
for /f "usebackq tokens=*" %%a in (`powershell -Command "(Invoke-RestMethod -Uri 'https://api.github.com/repos/Ultimaker/CuraEngine/releases/latest').tag_name"`) do (
    set "LATEST_RELEASE=%%a"
)

if "%LATEST_RELEASE%"=="" (
    echo Failed to get latest release, using fallback version 5.6.0
    set "LATEST_RELEASE=5.6.0"
)

echo Downloading CuraEngine version: %LATEST_RELEASE%

set "BINARY_URL=https://github.com/Ultimaker/CuraEngine/releases/download/%LATEST_RELEASE%/CuraEngine-win64.exe"
set "TEMP_BIN=%TEMP%\CuraEngine.exe"

powershell -Command "try { Invoke-WebRequest -Uri '%BINARY_URL%' -OutFile '%TEMP_BIN%' } catch { exit 1 }"

if errorlevel 1 (
    echo Failed to download pre-built Windows binary. 
    echo Please download manually from: https://github.com/Ultimaker/CuraEngine/releases
    pause
    exit /b 1
)

echo Installing...
move /y "%TEMP_BIN%" "%INSTALL_DIR%\CuraEngine.exe" >nul
copy /y "%INSTALL_DIR%\CuraEngine.exe" "%INSTALL_DIR%\CuraEngine4.exe" >nul

echo Done!
"%INSTALL_DIR%\CuraEngine.exe" --version
echo Add %INSTALL_DIR% to your system PATH if it is not already.
pause
