#!/usr/bin/env bash
set -e

INSTALL_DIR="/usr/local/bin"

echo "Installing CuraEngine for macOS..."

# Check if already installed
if command -v CuraEngine &> /dev/null; then
    echo "CuraEngine already installed!"
    CuraEngine --version
    exit 0
fi

# Download pre-built binary from Ultimaker
echo "Downloading CuraEngine binary..."
cd /tmp

# Try to get the latest release
LATEST_RELEASE=$(curl -s https://api.github.com/repos/Ultimaker/CuraEngine/releases/latest | grep '"tag_name"' | cut -d'"' -f4)

if [ -z "$LATEST_RELEASE" ]; then
    echo "Failed to get latest release, using fallback version"
    LATEST_RELEASE="5.6.0"
fi

echo "Downloading CuraEngine version: $LATEST_RELEASE"

BINARY_URL="https://github.com/Ultimaker/CuraEngine/releases/download/$LATEST_RELEASE/CuraEngine-macos"
if ! curl -f -L -o CuraEngine "$BINARY_URL"; then
    echo "No pre-built macOS binary found on GitHub via Ultimaker releases."
    echo "Attempting to install via Homebrew..."
    if command -v brew &> /dev/null; then
        brew install curaengine
        if command -v CuraEngine &> /dev/null; then
            sudo ln -sf $(command -v CuraEngine) /usr/local/bin/CuraEngine4
            echo "Installed via Homebrew!"
            exit 0
        fi
    else
        echo "Homebrew not found. Please install manual via https://github.com/Ultimaker/CuraEngine/releases"
        exit 1
    fi
else
    # Binary downloaded successfully
    sudo chmod +x CuraEngine
    sudo mv CuraEngine "$INSTALL_DIR/"
    sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
fi

echo "Done!"
CuraEngine --version
