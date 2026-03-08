#!/bin/bash
# Katana Auto-Installer for Linux

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}⚔  Katana Linux Auto-Installer  ⚔${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"

if [ -f /etc/debian_version ]; then PM="apt"; elif [ -f /etc/redhat-release ]; then PM="dnf"; elif [ -f /etc/arch-release ]; then PM="pacman"; elif [ -f /etc/os-release ]; then . /etc/os-release; case "$ID" in ubuntu|debian|pop|kali|linuxmint) PM="apt" ;; fedora|rhel|centos) PM="dnf" ;; arch|manjaro) PM="pacman" ;; suse|opensuse*) PM="zypper" ;; *) PM="unknown" ;; esac; else PM="unknown"; fi

echo -e "▸ Detected package manager: ${CYAN}$PM${NC}"

install_deps() {
    echo -e "▸ Installing dependencies..."
    case "$PM" in
        apt) sudo apt update && sudo apt install -y python3 python3-venv git curl wget perl openscad cura-engine ;;
        dnf) sudo dnf install -y python3 git curl wget perl openscad CuraEngine ;;
        pacman) sudo pacman -Sy --noconfirm python git curl wget perl openscad curaengine ;;
        zypper) sudo zypper install -y python3 git curl wget perl openscad CuraEngine ;;
        *) echo -e "${RED}✗ Unsupported distribution.${NC}"; exit 1 ;;
    esac
}

# Ensure CuraEngine is available (faster than Slic3r)
check_curaengine() {
    if ! command -v CuraEngine &> /dev/null && ! command -v curaengine &> /dev/null; then
        echo -e "${YELLOW}⚠ CuraEngine not found in PATH${NC}"
        echo -e "  CuraEngine is significantly faster than Slic3r"
        echo -e "  Install with: sudo apt install cura-engine (Debian/Ubuntu)"
    else
        echo -e "${GREEN}✓ CuraEngine found (fast slicing enabled)${NC}"
    fi
}

if ! command -v python3 &> /dev/null || ! command -v git &> /dev/null || ! command -v curl &> /dev/null; then install_deps; fi

# Ensure OpenSCAD is present even when core deps were already installed.
if ! command -v openscad &> /dev/null; then
    echo -e "▸ Installing OpenSCAD..."
    case "$PM" in
        apt) sudo apt update && sudo apt install -y openscad ;;
        dnf) sudo dnf install -y openscad ;;
        pacman) sudo pacman -Sy --noconfirm openscad ;;
        zypper) sudo zypper install -y openscad ;;
        *) echo -e "${YELLOW}⚠ Could not auto-install OpenSCAD for package manager: $PM${NC}" ;;
    esac
fi

# Create and enter Katana directory
INSTALL_DIR="$HOME/Katana"
echo -e "▸ Creating install directory: ${CYAN}$INSTALL_DIR${NC}"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR" || { echo -e "${RED}✗ Failed to enter $INSTALL_DIR${NC}"; exit 1; }

echo -e "▸ Downloading Katana installer..."
INSTALLER_URL="https://raw.githubusercontent.com/JohnnyTech-PRINTR-Cyan/Katana/main/install.py"
curl -LO $INSTALLER_URL || wget $INSTALLER_URL

if [ -f "install.py" ]; then
    echo -e "▸ Launching Katana installer..."
    python3 install.py
else
    echo -e "${RED}✗ Failed to download installer.${NC}"
    exit 1
fi
