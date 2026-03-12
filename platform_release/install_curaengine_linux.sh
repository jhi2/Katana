#!/usr/bin/env bash
set -e

INSTALL_DIR="/usr/local/bin"

echo "Installing CuraEngine..."

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

# Try different binary names
BINARY_URL="https://github.com/Ultimaker/CuraEngine/releases/download/$LATEST_RELEASE/CuraEngine"
if ! curl -f -L -o CuraEngine "$BINARY_URL"; then
    # Try with .linux suffix
    BINARY_URL="https://github.com/Ultimaker/CuraEngine/releases/download/$LATEST_RELEASE/CuraEngine-linux"
    if ! curl -f -L -o CuraEngine "$BINARY_URL"; then
        echo "No pre-built binary found. Building from source with Conan..."
        echo "⚠️  This will use significant CPU resources and may take 10-30 minutes"
        echo "    The build will leave 2 CPU cores free to keep your system responsive"
        
        # Install dependencies
        sudo apt update
        sudo apt install -y python3 python3-pip python3-venv ninja-build cmake git
        
        # Install Conan using pipx (recommended for system packages)
        if command -v pipx &> /dev/null; then
            pipx install conan==2.7.1
        else
            # Install pipx first
            sudo apt install -y pipx
            pipx install conan==2.7.1
            sudo pipx ensurepath  # Add pipx to PATH
        fi
        
        # Or fallback to venv
        if ! command -v conan &> /dev/null; then
            echo "Using virtual environment for Conan..."
            VENV_DIR=$(mktemp -d)
            python3 -m venv "$VENV_DIR"
            source "$VENV_DIR/bin/activate"
            pip install conan==2.7.1
        fi
        
        # Configure Conan
        conan config install https://github.com/ultimaker/conan-config.git
        conan profile detect --force
        
        BUILD_DIR=$(mktemp -d)
        cd "$BUILD_DIR"
        
        git clone https://github.com/Ultimaker/CuraEngine.git
        cd CuraEngine
        
        # Install and build with Conan (limited resources)
        conan install . --build=missing --update
        cmake --preset conan-release
        # Use fewer CPU cores to prevent system lag
        CORES=$(nproc)
        if [ $CORES -gt 2 ]; then
            CORES=$((CORES - 2))  # Leave 2 cores free
        fi
        cmake --build --preset conan-release --parallel $CORES
        
        # Copy the binary
        sudo cp build/Release/CuraEngine "$INSTALL_DIR/"
        sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
        cd /
        rm -rf "$BUILD_DIR"
    else
        # Binary downloaded successfully
        sudo chmod +x CuraEngine
        sudo mv CuraEngine "$INSTALL_DIR/"
        sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
    fi
else
    # Binary downloaded successfully
    sudo chmod +x CuraEngine
    sudo mv CuraEngine "$INSTALL_DIR/"
    sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
fi

echo "Done!"
CuraEngine --version