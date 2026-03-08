# Katana Release Notes

## Version 2.0.0

### 🚀 Major Features
- **Integrated 3D Slicer Workspace**: Added a full Three.js-based slice workspace with multi-plate support, project persistence, and transform controls.
- **Local Model Upload Pipeline**: Replaced URL-based STL import with server upload flow using Bulma file input and backend upload endpoint.
- **Project-Gated Slicing Flow**: Slice tab is now locked until a project is created or opened, preventing invalid empty workspace states.

### 🎨 UI & UX
- **Floating Tool Column**: Added Cura/Prusa-inspired floating slicer tools for move, rotate, scale, and delete-selected actions.
- **Improved Icon Rendering**: Fixed Font Awesome glyph issues caused by global font overrides.
- **More Reliable Slicer Startup**: Improved tab visibility/init behavior to avoid blank viewport rendering.

### 🔧 Reliability & Security
- **Three.js Load Stability**: Vendored Three.js locally and removed duplicate-instance loading paths.
- **Thumbnail Reliability**: Project thumbnails are now persisted as static PNG files and referenced by stable URLs.
- **Upload Hygiene**: Added startup cleanup of orphaned uploaded STL files not referenced by any saved project.
- **Config/Path Hardening**: Improved path handling and safer config write behavior.

---

## Version 1.0.5

### 🚀 New Features
- **✨ Connect to Cyan (Magic Sync)**: Seamlessly import printer configurations from other Katana/Cyan instances via URL.
- **Navbar Project Display**: Added "Current Project" status indicator to the top navigation bar for better workflow visibility.

### 🎨 UI & UX Polish
- **Branding Refresh**: Updated setup wizard terminology to focus on "Cyan" ecosystem integration.
- **Enhanced Setup Wizard**: Improved button spacing, iconography, and animations (pulsing sync icons).
- **Smooth Transitions**: Implemented fade-in animations for tab switching in the main dashboard.
- **Faster Boot**: Significantly reduced splash screen duration (from 15s to 3s) for a snappier startup experience.

### 🔧 Technical Changes
- **Blank Canvas**: Stripped legacy content from main dashboard tabs to prepare for the upcoming 2.0.0 "Content Update".
- **Robust Downloader**: Improved `/download_config` logic to automatically handle varied URL formats (trailing slashes, explicit file paths).

---

## Version 1.0.4

### 🚀 New Features
- **Config Downloader**: Initial implementation of the remote configuration import tool.
- **Wizard Integration**: Added the download/import flow as a primary option during initial installation.

---

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
