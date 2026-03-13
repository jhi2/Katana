@echo off
setlocal enabledelayedexpansion

echo Installing CuraEngine from source for Windows...

REM Define target directory
set "INSTALL_DIR=%USERPROFILE%\Katana\bin"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Check if already installed
if exist "%INSTALL_DIR%\CuraEngine.exe" (
    echo CuraEngine already installed at %INSTALL_DIR%\CuraEngine.exe
    "%INSTALL_DIR%\CuraEngine.exe" help
    goto :eof
)

REM Prerequisites
where git >nul 2>&1 || (
    echo git not found in PATH. Install Git and re-run this script.
    exit /b 1
)
where cmake >nul 2>&1 || (
    echo CMake not found in PATH. Install CMake and re-run this script.
    exit /b 1
)
where python >nul 2>&1 || (
    echo Python not found in PATH. Install Python 3.10+ and re-run this script.
    exit /b 1
)

REM Determine target release tag (4.x)
for /f "usebackq tokens=*" %%a in (`powershell -Command "(Invoke-RestMethod -Uri 'https://api.github.com/repos/Ultimaker/CuraEngine/releases').tag_name | Where-Object { $_ -match '^4\.' } | Select-Object -First 1"`) do (
    set "LATEST_RELEASE=%%a"
)

if "%LATEST_RELEASE%"=="" (
    echo Failed to get latest 4.x release, using fallback version 4.13.1
    set "LATEST_RELEASE=4.13.1"
)

echo Building CuraEngine version: %LATEST_RELEASE%

set "BUILD_DIR=%TEMP%\curaengine_build"
if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
mkdir "%BUILD_DIR%"

pushd "%BUILD_DIR%"

git clone https://github.com/Ultimaker/CuraEngine.git
if errorlevel 1 (
    echo Failed to clone CuraEngine repository.
    popd
    exit /b 1
)

cd CuraEngine

git checkout %LATEST_RELEASE%
if errorlevel 1 (
    echo Failed to checkout tag %LATEST_RELEASE%.
    popd
    exit /b 1
)

REM Install Conan (user scope)
python -m pip install --upgrade pip
python -m pip install conan==2.7.1

REM Configure Conan
python -m conan config install https://github.com/ultimaker/conan-config.git
python -m conan profile detect --force

REM Build
python -m conan install . --build=missing --update
cmake --preset conan-release

set "CORES=%NUMBER_OF_PROCESSORS%"
set /a CORES=%CORES%-2
if %CORES% LSS 1 set "CORES=1"
cmake --build --preset conan-release --parallel %CORES%

REM Copy the binary
if exist build\Release\CuraEngine.exe (
    copy /y build\Release\CuraEngine.exe "%INSTALL_DIR%\CuraEngine.exe" >nul
) else if exist build\CuraEngine.exe (
    copy /y build\CuraEngine.exe "%INSTALL_DIR%\CuraEngine.exe" >nul
) else (
    echo Build completed but CuraEngine.exe not found.
    popd
    exit /b 1
)

copy /y "%INSTALL_DIR%\CuraEngine.exe" "%INSTALL_DIR%\CuraEngine4.exe" >nul

popd
rmdir /s /q "%BUILD_DIR%"

echo Done!
"%INSTALL_DIR%\CuraEngine.exe" help

echo Add %INSTALL_DIR% to your system PATH if it is not already.
pause
