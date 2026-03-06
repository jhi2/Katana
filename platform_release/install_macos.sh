#!/bin/bash
# Katana Auto-Installer for macOS

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}⚔  Katana macOS Auto-Installer  ⚔${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════${NC}"

if ! command -v brew &> /dev/null; then
    echo -e "▸ Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    [ -d "/opt/homebrew/bin" ] && eval "$(/opt/homebrew/bin/brew shellenv)"
    [ -d "/usr/local/bin" ] && eval "$(/usr/local/bin/brew shellenv)"
fi

echo -e "▸ Ensuring dependencies..."
brew install python git curl

echo -e "▸ Downloading Katana installer..."
INSTALLER_URL="https://raw.githubusercontent.com/JohnnyTech-PRINTR-Cyan/Katana/main/install.py"
curl -LO $INSTALLER_URL

if [ -f "install.py" ]; then
    echo -e "▸ Launching Katana installer..."
    python3 install.py
else
    echo -e "${RED}✗ Failed to download installer.${NC}"; exit 1
fi
