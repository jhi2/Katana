# Katana

Katana is a desktop-first Flask + WebUI app for managing 3D printing projects and preparing models in a browser-based workspace.

For version history and changes, see [RELEASE_NOTES.md](./RELEASE_NOTES.md).

## What It Does

- Project-based workflow (create/open/save/delete projects)
- 3D workspace powered by Three.js
- STL upload to local server storage
- Multi-plate workspace controls
- Transform tools (move/rotate/scale/delete selected)
- Autosave for project state
- Persistent project thumbnails
- Printer profile setup + config import flow

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
4. Upload STL(s) from the workspace panel.
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
- `POST /api/upload_model` upload STL
- `GET /api/config` read current config

## Development

Run tests:

```bash
./venv/bin/python -m unittest discover -s tests -v
```

## License

AGPL-3.0. See [LICENSE](./LICENSE).
