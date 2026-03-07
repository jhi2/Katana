# Katana Release Notes

## Version 1.0.3

### 🚀 New Features
- **Printer Setup System**: Complete printer profile management with pre-built profiles (Ender 3, Prusa i3 MK3S+, Ultimaker S5, Bambu Lab A1 Mini)
- **Print3r Integration**: Added support for Print3r Perl-based CLI tool with CuraEngine preference
- **Enhanced Installers**: Cross-platform installers now handle dependency installation (Perl, OpenSCAD, CuraEngine)

### 🐛 Bug Fixes
- **Critical Security Fix**: Fixed INSTALL_DIR to always use `~/Katana` instead of script location (prevents accidental directory deletion)
- **Installer Stability**: Fixed premature exit when user presses 'y' to overwrite existing installation
- **Resource Management**: CuraEngine build now uses fewer CPU cores to prevent system lag
- **Python Environment**: Fixed externally-managed Python environment issues using pipx/virtual environments

### 🔧 Technical Changes
- **ConfigManager**: Extended with printer profile management methods
- **Flask Routes**: Added `/printer_setup`, `/save_custom_printer`, `/save_printer_selection`
- **Build System**: CuraEngine now built with Conan 2.7.1 for proper dependency management
- **Git Operations**: Improved clone logic to handle edge cases with existing directories

### 📦 Dependencies
- **Linux**: Perl, OpenSCAD, CuraEngine (built from source with Conan)
- **Windows**: StrawberryPerl, OpenSCAD, manual CuraEngine installation
- **macOS**: Perl (included), OpenSCAD, CuraEngine via Homebrew

### ⚠️ Important Notes
- **CuraEngine**: Standalone engine only (not full Ultimaker Cura application)
- **Performance**: CuraEngine is ~2x faster than Slic3r for most models
- **Resource Usage**: CuraEngine compilation may take 10-30 minutes on first run

---

## Version 1.0.2

### 🐛 Bug Fixes
- Security checks added for printer setup system
- Fixed configuration validation issues

---

## Version 1.0.1

### 🚀 New Features
- Added config manager and printer setup functionality
- Implemented welcome flow with printer selection
- Added base layout templates

---

## Version 1.0.0

### 🎉 Initial Release
- Basic Katana application with Flask UI
- Printer configuration system
- Integration with Klipper/Fluidd
