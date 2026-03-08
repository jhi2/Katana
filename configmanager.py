import os
import shutil as sh
import subprocess as sub
import json
import threading
import base64
import binascii
import time
from datetime import datetime
from validators import validate_file_path, validate_printer_profiles_file

class ConfigManager:
    def __init__(self):
        self.config = {}
        self.printer_profiles = {}
        self._config_cache = {}
        self._profiles_cache = {}
        self._config_mtime = {}
        self._profiles_mtime = {}
        self._lock = threading.Lock()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Ensure projects directory exists
        self.projects_dir = os.path.join(self.base_dir, "projects")
        if not os.path.exists(self.projects_dir):
            os.makedirs(self.projects_dir)
        self.thumbnail_dir = os.path.join(self.base_dir, "static", "thumbnails")
        if not os.path.exists(self.thumbnail_dir):
            os.makedirs(self.thumbnail_dir)
        self.uploads_dir = os.path.join(self.base_dir, "static", "uploads")
        if not os.path.exists(self.uploads_dir):
            os.makedirs(self.uploads_dir)

    def _resolve_path(self, relative_path):
        return validate_file_path(relative_path, base_dir=self.base_dir)

    def _resolve_project_path(self, filename):
        if not isinstance(filename, str) or not filename.endswith(".json"):
            raise ValueError("Invalid project filename")
        return validate_file_path(filename, base_dir=self.projects_dir)

    def _thumbnail_relpath(self, safe_name):
        return f"thumbnails/{safe_name}.png"

    def _thumbnail_abspath(self, safe_name):
        return validate_file_path(f"{safe_name}.png", base_dir=self.thumbnail_dir)

    def _persist_thumbnail(self, safe_name, thumbnail_data):
        if not isinstance(thumbnail_data, str) or not thumbnail_data.startswith("data:image/png;base64,"):
            return ""
        try:
            encoded = thumbnail_data.split(",", 1)[1]
            raw = base64.b64decode(encoded, validate=True)
            thumb_path = self._thumbnail_abspath(safe_name)
            with open(thumb_path, "wb") as f:
                f.write(raw)
            return "/static/" + self._thumbnail_relpath(safe_name)
        except (IndexError, ValueError, binascii.Error, OSError):
            return ""

    def check_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = self._resolve_path(dir)
            return os.path.exists(validated_path)
        except Exception:
            return False

    def save_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = self._resolve_path(dir)
            
            with self._lock:
                # Create backup if file exists
                if os.path.exists(validated_path):
                    backup_path = validated_path + ".bak"
                    sh.copy2(validated_path, backup_path)
                
                # Write config with atomic operation
                temp_path = validated_path + ".tmp"
                with open(temp_path, "w") as f:
                    json.dump(self.config, f, indent=4)
                
                # Atomic move
                os.replace(temp_path, validated_path)
                
                # Update cache
                self._config_cache[validated_path] = self.config.copy()
                self._config_mtime[validated_path] = datetime.now().timestamp()
                
        except (OSError, IOError, TypeError, ValueError) as e:
            raise Exception(f"Failed to save config: {str(e)}")

    def load_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = self._resolve_path(dir)
            
            # Simplified loading without caching for now to debug
            if os.path.exists(validated_path):
                with open(validated_path, "r") as f:
                    self.config = json.load(f)
            else:
                # Create default config
                self.config = {"printers": []}
                self.save_config(dir)
                    
        except Exception as e:
            # Fallback to default config
            self.config = {"printers": []}
    
    def load_printer_profiles(self, profiles_dir):
        try:
            # Validate and normalize the file path
            validated_path = self._resolve_path(profiles_dir)
            
            # Simplified loading without caching for now to debug
            if os.path.exists(validated_path):
                with open(validated_path, "r") as f:
                    data = json.load(f)
                    self.printer_profiles = data.get("profiles", [])
            else:
                self.printer_profiles = []
                    
        except Exception as e:
            # Fallback to empty profiles
            self.printer_profiles = []
    
    def get_printer_profiles(self):
        return self.printer_profiles
    
    def save_printer_to_config(self, printer_data):
        try:
            if not isinstance(printer_data, dict):
                raise ValueError("Printer data must be a dictionary")
                
            if "printers" not in self.config:
                self.config["printers"] = []
            
            # Validate printer data structure
            required_fields = ["name", "manufacturer", "bed_size", "nozzle_size"]
            for field in required_fields:
                if field not in printer_data:
                    raise ValueError(f"Missing required field: {field}")
            
            self.config["printers"].append({"data": printer_data})
            
        except Exception as e:
            raise Exception(f"Failed to save printer to config: {str(e)}")
    
    def get_saved_printers(self):
        try:
            printers = self.config.get("printers", [])
            if not isinstance(printers, list):
                return []
            
            # Validate structure
            validated_printers = []
            for printer in printers:
                if isinstance(printer, dict) and "data" in printer:
                    validated_printers.append(printer)
            
            return validated_printers
        except Exception:
            return []

    def list_projects(self):
        try:
            projects = []
            if not os.path.exists(self.projects_dir):
                return []
                
            for filename in os.listdir(self.projects_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self.projects_dir, filename)
                    with open(filepath, "r") as f:
                        data = json.load(f)
                        # Extract metadata
                        projects.append({
                            "name": data.get("name", filename.replace(".json", "")),
                            "filename": filename,
                            "modified": datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d %H:%M:%S"),
                            "thumbnail": data.get("thumbnail", "")
                        })
            return sorted(projects, key=lambda x: x['modified'], reverse=True)
        except Exception as e:
            print(f"Error listing projects: {e}")
            return []

    def save_project(self, name, project_data, previous_filename=None):
        try:
            if not name:
                raise ValueError("Project name is required")
            
            # Clean name for filename
            safe_name = "".join([c for c in name if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
            if not safe_name:
                raise ValueError("Project name contains no valid filename characters")
            filename = f"{safe_name}.json"
            filepath = self._resolve_project_path(filename)
            previous_path = None
            previous_base = None

            if previous_filename:
                previous_path = self._resolve_project_path(previous_filename)
                previous_base = os.path.splitext(os.path.basename(previous_filename))[0]

                if previous_filename != filename and os.path.exists(filepath):
                    raise ValueError("A project with that name already exists")

            # Persist thumbnail image as a static file for reliable loading.
            thumb_safe_name = safe_name.replace(" ", "_")
            thumb_url = self._persist_thumbnail(thumb_safe_name, project_data.get("thumbnail", ""))
            if thumb_url:
                project_data["thumbnail"] = thumb_url
            
            project_data["name"] = name
            project_data["last_modified"] = datetime.now().isoformat()
            
            with open(filepath, "w") as f:
                json.dump(project_data, f, indent=4)

            # If this was a rename, remove the old project file and stale thumbnail.
            if previous_path and previous_filename != filename and os.path.exists(previous_path):
                os.remove(previous_path)
                if previous_base:
                    old_thumb = self._thumbnail_abspath(previous_base.replace(" ", "_"))
                    if os.path.exists(old_thumb):
                        os.remove(old_thumb)
                
            return True, filename
        except Exception as e:
            return False, str(e)

    def load_project(self, filename):
        try:
            filepath = self._resolve_project_path(filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Project {filename} not found")
                
            with open(filepath, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
    
    def delete_project(self, filename):
        try:
            filepath = self._resolve_project_path(filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False

    def cleanup_orphan_uploads(self):
        try:
            referenced = set()

            def _collect_referenced_models(models):
                if not isinstance(models, list):
                    return
                for model in models:
                    if not isinstance(model, dict):
                        continue
                    model_url = model.get("url", "")
                    if isinstance(model_url, str) and model_url.startswith("/static/uploads/"):
                        referenced.add(model_url.rsplit("/", 1)[-1])

            if os.path.exists(self.projects_dir):
                for filename in os.listdir(self.projects_dir):
                    if not filename.endswith(".json"):
                        continue
                    project_path = os.path.join(self.projects_dir, filename)
                    try:
                        with open(project_path, "r") as f:
                            project_data = json.load(f)
                        # Current schema
                        _collect_referenced_models(project_data.get("models", []))
                        # Backward-compatible schema variants
                        if isinstance(project_data.get("data"), dict):
                            _collect_referenced_models(project_data["data"].get("models", []))
                    except Exception:
                        continue

            removed = 0
            now = time.time()
            max_age_seconds = 7 * 24 * 60 * 60  # keep unreferenced uploads for 7 days
            for entry in os.scandir(self.uploads_dir):
                if not entry.is_file():
                    continue
                if not entry.name.lower().endswith(".stl"):
                    continue
                if entry.name not in referenced:
                    try:
                        age_seconds = now - entry.stat().st_mtime
                        if age_seconds < max_age_seconds:
                            continue
                        os.remove(entry.path)
                        removed += 1
                    except OSError:
                        continue
            return removed
        except Exception:
            return 0
