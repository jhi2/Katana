#!/usr/bin/env bash
set -e

INSTALL_DIR="/usr/local/bin"

echo "Installing CuraEngine from source (macOS)..."

# Check if already installed
if command -v CuraEngine &> /dev/null; then
    echo "CuraEngine already installed!"
    CuraEngine help
    exit 0
fi

# Ensure Xcode CLI tools are available
if ! xcode-select -p >/dev/null 2>&1; then
    echo "Xcode Command Line Tools not found. Install with: xcode-select --install"
    exit 1
fi

# Ensure Homebrew is available for dependencies
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Install from https://brew.sh and re-run this script."
    exit 1
fi

# Determine target release tag (4.x)
LATEST_RELEASE=$(curl -s https://api.github.com/repos/Ultimaker/CuraEngine/releases \
    | grep '"tag_name"' \
    | cut -d'"' -f4 \
    | grep -E '^4\.' \
    | head -n 1)

if [ -z "$LATEST_RELEASE" ]; then
    echo "Failed to get latest 4.x release, using fallback version"
    LATEST_RELEASE="4.13.1"
fi

echo "Building CuraEngine version: $LATEST_RELEASE"

# Install dependencies
brew install git cmake ninja pkg-config python@3.12 pipx || true

# Install Conan using pipx
if command -v pipx &> /dev/null; then
    if command -v python3.12 &> /dev/null; then
        pipx install --python python3.12 conan==2.7.1
    else
        pipx install conan==2.7.1
    fi
else
    echo "pipx not available; install with: brew install pipx"
    exit 1
fi

# Or fallback to venv
if ! command -v conan &> /dev/null; then
    echo "Using virtual environment for Conan..."
    VENV_DIR=$(mktemp -d)
    if command -v python3.12 &> /dev/null; then
        python3.12 -m venv "$VENV_DIR"
    else
        python3 -m venv "$VENV_DIR"
    fi
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
# Build the same version we attempted to download.
git checkout "$LATEST_RELEASE"

# Fix missing cstdint include on some toolchains.
python3 - <<'PY'
from pathlib import Path

math_h = Path("src/utils/math.h")
if math_h.exists():
    text = math_h.read_text()
    if "#include <cstdint>" not in text:
        lines = text.splitlines()
        out = []
        inserted = False
        for line in lines:
            out.append(line)
            if line.strip() == "#include <cmath>" and not inserted:
                out.append("#include <cstdint>")
                inserted = True
        if not inserted:
            out.insert(0, "#include <cstdint>")
        math_h.write_text("\n".join(out) + "\n")
PY

# Use fewer CPU cores to prevent system lag
CORES=$(sysctl -n hw.ncpu)
if [ $CORES -gt 2 ]; then
    CORES=$((CORES - 2))  # Leave 2 cores free
fi

if [ -f conanfile.txt ] || [ -f conanfile.py ]; then
    conan install . --build=missing --update
    cmake --preset conan-release
    cmake --build --preset conan-release --parallel $CORES

    # Copy the binary
    sudo cp build/Release/CuraEngine "$INSTALL_DIR/"
else
    echo "No Conan recipe found. Please check the CuraEngine repository."
    exit 1
fi

sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
cd /
rm -rf "$BUILD_DIR"

echo "Done!"
CuraEngine help
