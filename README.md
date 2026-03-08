# Katana

Katana is a desktop-first Flask + WebUI app for managing 3D printing projects and preparing models in a browser-based workspace.

For version history and changes, see [RELEASE_NOTES.md](./RELEASE_NOTES.md).

## What It Does

- Project-based workflow (create/open/save/delete projects)
- 3D workspace powered by Three.js
- STL + 3MF upload to local server storage
- Drag-and-drop model upload in Slice tab
- Multi-plate workspace controls
- Multi-plate save/load persistence
- Transform tools (move/rotate/scale/delete selected)
- Overhang preview coloring (red) on model surfaces
- Placement warning notification for collision/off-plate
- Autosave for project state
- Persistent project thumbnails
- Pin/unpin projects in Home view
- Printer profile setup + config import flow
- Built-in seeded demo project (`Demo Block`)

## Current State

Katana currently focuses on project/workspace management and model staging.

- There is a **Slice** placeholder button in the UI.
- Actual slicing pipeline execution is not implemented yet in the main workspace (`alert("no slicer yet")` placeholder).

## Requirements

- Python `3.12+` recommended
- Linux/macOS/Windows with a GUI environment for splash + FlaskWebGUI mode

Python dependencies are in [requirements.txt](./requirements.txt).

## Quick Start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

If you want to run without splash behavior, use:

```bash
python main.py --no-gui
```

## Basic Workflow

1. Open Katana.
2. Create a project (Home tab -> New Project modal) or open an existing one.
3. Go to Slice tab.
4. Upload STL/3MF from the workspace panel, or drag files into the Slice viewport.
5. Arrange models and save (autosave also runs in background).

## Project Layout

- [main.py](./main.py): app entrypoint + splash + FlaskWebGUI launch
- [ui.py](./ui.py): Flask routes/API
- [configmanager.py](./configmanager.py): config + project persistence
- [templates/index.html](./templates/index.html): main UI
- [static/placer.js](./static/placer.js): Three.js slicer workspace logic
- `projects/`: saved project JSON files
- `static/uploads/`: uploaded STL files
- `static/thumbnails/`: generated project thumbnail images

## API Endpoints (Core)

- `GET /api/projects` list projects
- `POST /api/projects` save project
- `GET /api/projects/<filename>` load project
- `DELETE /api/projects/<filename>` delete project
- `POST /api/upload_model` upload STL/3MF (3MF extracts mesh models only)
- `GET /api/config` read current config
- `GET /demo/block.stl` demo model file route

## Development

Run tests:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## License

AGPL-3.0. See [LICENSE](./LICENSE).
