#!/usr/bin/env python3
"""
Katana Installer
Clones the repository, installs dependencies, and creates a desktop entry.
Supports Linux, macOS, and Windows.

Usage:
    python3 install.py
    python3 install.py --uninstall
"""

import os
import sys
import shutil
import platform
import subprocess
import getpass


# ─── Configuration ────────────────────────────────────────────────────────────

REPO_URL = "https://github.com/JohnnyTech-PRINTR-Cyan/Katana.git"
APP_NAME = "Katana"
APP_COMMENT = "Katana Application"
CATEGORIES = "Utility;Development;"

SYSTEM = platform.system().lower()
USERNAME = getpass.getuser()
HOME = os.path.expanduser("~")

# Install paths
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))

VENV_DIR = os.path.join(INSTALL_DIR, ".venv")
APP_DIR = INSTALL_DIR  # The repo itself is the app directory
ICON_PATH = os.path.join(INSTALL_DIR, "static", "icon.png")
REQUIREMENTS = os.path.join(INSTALL_DIR, "requirements.txt")
MAIN_SCRIPT = os.path.join(INSTALL_DIR, "main.py")


# ─── Utilities ────────────────────────────────────────────────────────────────

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    @staticmethod
    def supports_color():
        if SYSTEM == "windows":
            return os.environ.get("WT_SESSION") is not None  # Windows Terminal
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def color(text, code):
    if Colors.supports_color():
        return f"{code}{text}{Colors.RESET}"
    return text


def header(msg):
    print(f"\n{color('═' * 60, Colors.CYAN)}")
    print(f"  {color(msg, Colors.BOLD + Colors.CYAN)}")
    print(f"{color('═' * 60, Colors.CYAN)}\n")


def step(msg):
    print(f"  {color('▸', Colors.GREEN)} {msg}")


def warn(msg):
    print(f"  {color('⚠', Colors.YELLOW)} {color(msg, Colors.YELLOW)}")


def error(msg):
    print(f"  {color('✗', Colors.RED)} {color(msg, Colors.RED)}")


def success(msg):
    print(f"  {color('✓', Colors.GREEN)} {color(msg, Colors.GREEN)}")


def run(cmd, cwd=None, check=True):
    """Run a shell command and stream output."""
    step(f"Running: {color(' '.join(cmd) if isinstance(cmd, list) else cmd, Colors.BLUE)}")
    result = subprocess.run(
        cmd, cwd=cwd, shell=isinstance(cmd, str),
        capture_output=False, text=True
    )
    if check and result.returncode != 0:
        error(f"Command failed with exit code {result.returncode}")
        sys.exit(1)
    return result


# ─── Check Prerequisites ─────────────────────────────────────────────────────

def check_prerequisites():
    header("Checking Prerequisites")

    # Python version
    py_ver = sys.version_info
    if py_ver < (3, 9):
        error(f"Python 3.9+ required, found {py_ver.major}.{py_ver.minor}")
        sys.exit(1)
    success(f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}")

    # Git
    if shutil.which("git") is None:
        error("Git is not installed. Please install git first.")
        sys.exit(1)
    success("Git is available")

    # pip / venv
    try:
        import venv  # noqa: F401
        success("venv module available")
    except ImportError:
        error("Python venv module not found. Install python3-venv.")
        sys.exit(1)


# ─── Clone Repository ────────────────────────────────────────────────────────

def clone_repo():
    header("Checking Repository")

    if os.path.exists(os.path.join(INSTALL_DIR, ".git")):
        success("Already in a git repository; skipping clone.")
        return

    if os.path.exists(INSTALL_DIR) and len(os.listdir(INSTALL_DIR)) > 1:
        warn(f"Directory already exists and is not empty: {INSTALL_DIR}")
        response = input(f"  {color('?', Colors.YELLOW)} Overwrite? [y/N]: ").strip().lower()
        if response in ("y", "yes"):
            step(f"Removing existing directory: {INSTALL_DIR}")
            shutil.rmtree(INSTALL_DIR)
        else:
            error("Installation cancelled.")
            sys.exit(1)

    run(["git", "clone", REPO_URL, INSTALL_DIR])
    success(f"Cloned to {INSTALL_DIR}")


# ─── Create Virtual Environment & Install Dependencies ───────────────────────

def setup_environment():
    header("Setting Up Python Environment")

    # Create venv
    step("Creating virtual environment...")
    run(["python3", "-m", "venv", VENV_DIR])
    success("Virtual environment created")

    # Determine pip path
    if SYSTEM == "windows":
        pip_path = os.path.join(VENV_DIR, "Scripts", "pip")
        python_path = os.path.join(VENV_DIR, "Scripts", "python")
    else:
        pip_path = os.path.join(VENV_DIR, "bin", "pip")
        python_path = os.path.join(VENV_DIR, "bin", "python")

    # Upgrade pip
    step("Upgrading pip...")
    run([python_path, "-m", "pip", "install", "--upgrade", "pip"])

    # Install requirements
    if os.path.exists(REQUIREMENTS):
        step("Installing dependencies from requirements.txt...")
        run([pip_path, "install", "-r", REQUIREMENTS])
        success("All dependencies installed")
    else:
        warn("No requirements.txt found, installing core dependencies...")
        run([pip_path, "install", "flask", "flaskwebgui", "waitress", "psutil"])
        success("Core dependencies installed")

    # Patch flaskwebgui if Python < 3.12
    if sys.version_info < (3, 12):
        step("Patching flaskwebgui for Python < 3.12 compatibility...")
        try:
            site_pkgs_cmd = [python_path, "-c", "import site; print(site.getsitepackages()[0])"]
            site_pkgs = subprocess.check_output(site_pkgs_cmd, text=True).strip()
            flaskwebgui_path = os.path.join(site_pkgs, "flaskwebgui.py")
            if os.path.exists(flaskwebgui_path):
                with open(flaskwebgui_path, 'r') as f:
                    content = f.read()
                
                bad_fstring = 'logger.info(f"Command: {\\" \\".join(self.browser_command)}")'
                good_code = '_cmd = " ".join(self.browser_command)\\n        logger.info(f"Command: {_cmd}")'
                
                if bad_fstring in content:
                    content = content.replace(bad_fstring, good_code)
                    with open(flaskwebgui_path, 'w') as f:
                        f.write(content)
                    success("flaskwebgui patched successfully")
                else:
                    success("flaskwebgui already compatible or patched")
        except Exception as e:
            warn(f"Failed to patch flaskwebgui: {e}")


# ─── Desktop Integration ─────────────────────────────────────────────────────

def create_desktop_entry_linux():
    """Create a .desktop file for Linux."""
    header("Creating Desktop Entry (Linux)")

    if SYSTEM == "windows":
        python_path = os.path.join(VENV_DIR, "Scripts", "python")
    else:
        python_path = os.path.join(VENV_DIR, "bin", "python")

    desktop_dir = os.path.join(HOME, ".local", "share", "applications")
    os.makedirs(desktop_dir, exist_ok=True)

    desktop_file = os.path.join(desktop_dir, "katana.desktop")
    desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment={APP_COMMENT}
Exec={python_path} {MAIN_SCRIPT}
Icon={ICON_PATH}
Terminal=false
Type=Application
Categories={CATEGORIES}
StartupWMClass=Katana
"""

    with open(desktop_file, "w") as f:
        f.write(desktop_content)

    os.chmod(desktop_file, 0o755)
    success(f"Desktop entry created: {desktop_file}")

    # Update desktop database
    run(["update-desktop-database", desktop_dir], check=False)
    success("Desktop database updated")


def create_desktop_entry_macos():
    """Create a launcher script for macOS."""
    header("Creating Application Launcher (macOS)")

    if SYSTEM == "windows":
        python_path = os.path.join(VENV_DIR, "Scripts", "python")
    else:
        python_path = os.path.join(VENV_DIR, "bin", "python")

    launcher_path = os.path.join(HOME, "Desktop", "Katana.command")
    launcher_content = f"""#!/bin/bash
cd "{INSTALL_DIR}"
"{python_path}" "{MAIN_SCRIPT}"
"""

    with open(launcher_path, "w") as f:
        f.write(launcher_content)

    os.chmod(launcher_path, 0o755)
    success(f"Launcher created: {launcher_path}")
    step("Tip: Drag this to your Dock for quick access")


def create_desktop_entry_windows():
    """Create a shortcut for Windows."""
    header("Creating Desktop Shortcut (Windows)")

    python_path = os.path.join(VENV_DIR, "Scripts", "pythonw.exe")

    # Create a .bat launcher
    launcher_path = os.path.join(HOME, "Desktop", "Katana.bat")
    launcher_content = f"""@echo off
cd /d "{INSTALL_DIR}"
"{python_path}" "{MAIN_SCRIPT}"
"""

    with open(launcher_path, "w") as f:
        f.write(launcher_content)

    success(f"Launcher created: {launcher_path}")

    # Try to create a proper shortcut via PowerShell
    shortcut_path = os.path.join(HOME, "Desktop", "Katana.lnk")
    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$shortcut = $ws.CreateShortcut('{shortcut_path}')
$shortcut.TargetPath = '{python_path}'
$shortcut.Arguments = '"{MAIN_SCRIPT}"'
$shortcut.WorkingDirectory = '{INSTALL_DIR}'
$shortcut.IconLocation = '{ICON_PATH}'
$shortcut.Description = '{APP_COMMENT}'
$shortcut.Save()
"""
    try:
        run(["powershell", "-Command", ps_script], check=False)
        success(f"Shortcut created: {shortcut_path}")
        # Remove .bat if .lnk was created
        if os.path.exists(shortcut_path):
            os.remove(launcher_path)
    except Exception:
        warn("Could not create .lnk shortcut, .bat launcher is available instead")


def create_desktop_entry():
    """Create a desktop entry/shortcut for the current platform."""
    if SYSTEM == "linux":
        create_desktop_entry_linux()
    elif SYSTEM == "darwin":
        create_desktop_entry_macos()
    elif SYSTEM == "windows":
        create_desktop_entry_windows()
    else:
        warn(f"Unsupported platform for desktop integration: {SYSTEM}")


# ─── Uninstall ────────────────────────────────────────────────────────────────

def uninstall():
    header(f"Uninstalling {APP_NAME}")

    # Remove install directory
    if os.path.exists(INSTALL_DIR):
        if os.path.exists(os.path.join(INSTALL_DIR, ".git")):
            warn(f"Refusing to delete {INSTALL_DIR} because it contains a .git repository.")
            warn("To uninstall completely, delete the directory manually.")
        else:
            step(f"Removing {INSTALL_DIR}...")
            shutil.rmtree(INSTALL_DIR)
            success("Application directory removed")
    else:
        warn("Application directory not found")

    # Remove desktop entry
    if SYSTEM == "linux":
        desktop_file = os.path.join(HOME, ".local", "share", "applications", "katana.desktop")
        if os.path.exists(desktop_file):
            os.remove(desktop_file)
            success("Desktop entry removed")
            run(["update-desktop-database", os.path.join(HOME, ".local", "share", "applications")], check=False)
    elif SYSTEM == "darwin":
        launcher = os.path.join(HOME, "Desktop", "Katana.command")
        if os.path.exists(launcher):
            os.remove(launcher)
            success("Launcher removed")
    elif SYSTEM == "windows":
        for ext in (".bat", ".lnk"):
            launcher = os.path.join(HOME, "Desktop", f"Katana{ext}")
            if os.path.exists(launcher):
                os.remove(launcher)
                success(f"Shortcut removed: Katana{ext}")

    success(f"{APP_NAME} has been uninstalled")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"""
{color('╔══════════════════════════════════════════════════════════╗', Colors.YELLOW)}
{color('║', Colors.YELLOW)}        {color('⚔  Katana Installer  ⚔', Colors.BOLD + Colors.YELLOW)}                        {color('║', Colors.YELLOW)}
{color('╚══════════════════════════════════════════════════════════╝', Colors.YELLOW)}
""")

    # Handle --uninstall flag
    if "--uninstall" in sys.argv:
        uninstall()
        return

    step(f"Platform:     {color(SYSTEM, Colors.CYAN)}")
    step(f"User:         {color(USERNAME, Colors.CYAN)}")
    step(f"Install path: {color(INSTALL_DIR, Colors.CYAN)}")
    print()

    response = input(f"  {color('?', Colors.YELLOW)} Proceed with installation? [Y/n]: ").strip().lower()
    if response in ("n", "no"):
        error("Installation cancelled.")
        sys.exit(0)

    check_prerequisites()
    clone_repo()
    setup_environment()
    create_desktop_entry()

    header("Installation Complete! 🎉")
    success(f"{APP_NAME} has been installed to {INSTALL_DIR}")

    if SYSTEM == "linux":
        python_path = os.path.join(VENV_DIR, "bin", "python")
    elif SYSTEM == "windows":
        python_path = os.path.join(VENV_DIR, "Scripts", "python")
    else:
        python_path = os.path.join(VENV_DIR, "bin", "python")

    print(f"\n  To run manually:")
    print(f"    {color(f'{python_path} {MAIN_SCRIPT}', Colors.CYAN)}")
    print(f"\n  To uninstall:")
    print(f"    {color(f'python3 install.py --uninstall', Colors.CYAN)}")
    print()


if __name__ == "__main__":
    main()
