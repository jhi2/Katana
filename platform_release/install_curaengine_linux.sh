#!/usr/bin/env bash
set -e

INSTALL_DIR="/usr/local/bin"

echo "Installing CuraEngine from source (Linux)..."

# Check if already installed
if command -v CuraEngine &> /dev/null; then
    echo "CuraEngine already installed!"
    CuraEngine help
    exit 0
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

# Install dependencies (per CuraEngine wiki)
sudo apt update
sudo apt install -y git make ninja-build cmake pkg-config
# Prefer newer toolchain if available
sudo apt install -y gcc-13 g++-13 || true
# Prefer Python 3.12+ if available
sudo apt install -y python3.12 python3.12-venv python3.12-dev || true
sudo apt install -y python3 python3-pip python3-venv
# SIP is required by the CMake FindSIP check; package names vary across distros.
if ! sudo apt install -y python3-sip python3-sip-dev; then
    sudo apt install -y sip-dev || true
fi

# Install Conan using pipx (recommended for system packages)
if command -v pipx &> /dev/null; then
    if command -v python3.12 &> /dev/null; then
        pipx install --python python3.12 conan==2.7.1
    else
        pipx install conan==2.7.1
    fi
else
    # Install pipx first
    sudo apt install -y pipx
    if command -v python3.12 &> /dev/null; then
        pipx install --python python3.12 conan==2.7.1
    else
        pipx install conan==2.7.1
    fi
    sudo pipx ensurepath  # Add pipx to PATH
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
CORES=$(nproc)
if [ $CORES -gt 2 ]; then
    CORES=$((CORES - 2))  # Leave 2 cores free
fi

if [ -f conanfile.txt ] || [ -f conanfile.py ]; then
    # Install and build with Conan (per CuraEngine wiki)
    if command -v gcc-13 &> /dev/null && command -v g++-13 &> /dev/null; then
        export CC=gcc-13
        export CXX=g++-13
    fi
    conan install . --build=missing --update
    cmake --preset conan-release
    cmake --build --preset conan-release --parallel $CORES

    # Copy the binary
    sudo cp build/Release/CuraEngine "$INSTALL_DIR/"
else
    echo "No Conan recipe found. Building with system dependencies..."

    sudo apt update
    sudo apt install -y build-essential pkg-config libprotobuf-dev libprotoc-dev protobuf-compiler
    # Ensure SIP is available for CMake FindSIP.
    if ! sudo apt install -y python3-sip python3-sip-dev; then
        sudo apt install -y sip-dev || true
    fi

    # Build libArcus from source to avoid ABI/API mismatches with distro packages.
    echo "Building libArcus from source for CuraEngine compatibility..."
    ARCUS_DIR=$(mktemp -d)
    git clone https://github.com/Ultimaker/libArcus.git "$ARCUS_DIR/libArcus"
    if git -C "$ARCUS_DIR/libArcus" rev-parse "$LATEST_RELEASE" >/dev/null 2>&1; then
        git -C "$ARCUS_DIR/libArcus" checkout "$LATEST_RELEASE"
    fi
    # Patch libArcus for protobuf API changes (SetTotalBytesLimit signature)
    export ARCUS_DIR
    python3 - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["ARCUS_DIR"]) / "libArcus"
socket_p = root / "src/Socket_p.h"
text = socket_p.read_text()
old = "stream.SetTotalBytesLimit(message_size_maximum, message_size_warning);"
if old in text:
    new = (
        "#if GOOGLE_PROTOBUF_VERSION >= 3020000\n"
        "        stream.SetTotalBytesLimit(message_size_maximum);\n"
        "#else\n"
        "        stream.SetTotalBytesLimit(message_size_maximum, message_size_warning);\n"
        "#endif"
    )
    text = text.replace(old, new)
    socket_p.write_text(text)
PY
    cmake -S "$ARCUS_DIR/libArcus" -B "$ARCUS_DIR/libArcus/build" \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local
    cmake --build "$ARCUS_DIR/libArcus/build" --parallel $CORES
    sudo cmake --install "$ARCUS_DIR/libArcus/build"
    rm -rf "$ARCUS_DIR"

    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH=/usr/local
    cmake --build build --parallel $CORES
    sudo cp build/CuraEngine "$INSTALL_DIR/"
fi
sudo ln -sf "$INSTALL_DIR/CuraEngine" "$INSTALL_DIR/CuraEngine4"
cd /
rm -rf "$BUILD_DIR"

echo "Done!"
CuraEngine help
