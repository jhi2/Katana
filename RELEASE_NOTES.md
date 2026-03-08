# Katana Release Notes

## Version 5.0.0

### 🚀 Major Features
- **Start Slice execution**: Prep modal now launches `print3r -vv` after baking and writes `gcode/<project>.gcode`.
- **Virtual Preview tab**: After slice succeeds, the new Preview tab unlocks with slider-driven virtual printer view plus G-code metadata.

### 🧰 Tooling & Toolchain
- **OpenSCAD enforced**: Installers explicitly install OpenSCAD before Print3r so baking works without manual setup.
- **Explicit Print3r output**: All generated commands pass `-o gcode/<project>.gcode` so preview state is deterministic.

---

## Version 4.0.0

### 🚀 Major Features
- **Slice Prep Pipeline**: Slice now performs a preparation workflow instead of immediate execution, including profile generation, model preprocessing, and command planning.
- **Transform Baking for Print3r Inputs**: Project model transforms (position/rotation/scale) are now baked into generated wrapper files under `./baked/<project>/plate_<n>/` and used for command generation.
- **Per-Plate Command Generation**: The backend now builds one Print3r command per populated build plate with separate output targets.

### 🧭 Workflow UX
- **Slice Plan Modal**: Added a preflight modal that shows what Slice prep will do before it runs.
- **Prep Log Modal (Terminal-Style)**: Added live, terminal-style prep output showing generated profile paths, baked files, and prepared command lines.
- **No Auto-Slice Execution Yet**: Prep flow still intentionally stops before running Print3r.

### 🔧 API & Integration
- **`/api/print3r/parse_commands`**: Added command parser endpoint that reads project/profile inputs and returns per-plate Print3r argument lists.
- **Bake Toggle Support**: Parser supports `bake_models` control and defaults to baked model inputs for prep flow.

---

## Version 3.0.0

### 🚀 Major Features
- **Print3r Profile Generation from Slice**: The Slice action now generates a Print3r printer profile file from the active project and settings without launching Print3r yet.
- **Profile Path Aligned with Print3r Docs**: Generated printer profiles are written to `./settings/printer/<project>.ini` (with a compatibility copy at `./settings/<project>.ini`) and can be referenced via `--printer=<project>`.
- **Settings/Profile Separation**: Printer identity and device profile remain in `config.json`, while print tuning values are managed independently in the Settings workflow and profile output.

### 🎛️ Settings Expansion
- **Expanded Print3r Setting Controls**: Added many additional settings in the Settings modal for Slic3r-focused tuning, including first-layer controls, more speed controls, thickness options, support angle, and fan controls.
- **Per-Project Settings Persistence**: Settings are stored per project and reapplied when generating profile INI files.

### 🔧 Integration Notes
- **No Automatic Slicing Execution Yet**: This release prepares the full profile/tuning pipeline and intentionally stops at profile generation.

---

## Version 2.1.0

### 🚀 New Features
- **3MF Model Import (Models Only)**: Added `.3mf` upload support that extracts mesh geometry into loadable models while ignoring print profiles/settings/project metadata.
- **Drag-and-Drop Upload in Slice Tab**: STL/3MF files can now be dropped directly into the workspace.
- **Pinned Projects**: Added project pin/unpin controls in Home; pinned projects sort above unpinned.
- **Demo Project Seeding**: Added tracked demo definition and startup seeding for "Demo Block".

### 🎨 UI & UX
- **Responsive Slice Layout**: Slice viewport now expands to fill available vertical space beneath tabs.
- **Improved Drop Overlay Layering**: File-drop overlay now appears above floating workspace controls.
- **Geometry Warning Toast**: Added corner warning notification for placement issues (collision/off-plate).
- **Modal-First Project Creation**: New project flow uses Bulma modal instead of browser prompt.

### 🔧 Behavior Fixes
- **Multi-Plate Persistence**: Project save/load now preserves plate count and active plate index.
- **Rename Without Duplication**: Project rename updates in place using `previous_filename` semantics.
- **Removed Orphan Upload Cleanup**: Automatic startup deletion of uploads has been removed.
- **Splash Handoff Smoothing**: Splash duration includes a handoff buffer to hide blank transition.

---

## Version 2.0.1

### 🐛 Bug Fixes
- **Project Rename Without Duplicates**: Renaming a project now updates the existing project record instead of creating duplicate project files.
- **Safer Rename Handling**: Added collision checks when renaming to an existing project name.

### 🚀 Improvements
- **Autosave System**: Added debounced + periodic autosave for slicer state changes, project name edits, model upload/load, and plate/model operations.
- **Create Project Modal**: Replaced browser `prompt()` with a native Bulma modal for cleaner project creation UX.
- **Bulma Layout Refactor**: Reduced inline styling and moved more UI structure to stock Bulma classes while preserving the existing visual design.

### 🔧 Reliability
- **Project Save Semantics**: Save API now supports `previous_filename` for consistent save/rename behavior from frontend autosave and manual save flows.

---

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
