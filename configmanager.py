import os
import shutil as sh
import subprocess as sub
import json
import threading
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

    def check_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = validate_file_path(dir)
            return os.path.exists(validated_path)
        except Exception:
            return False
    def save_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = validate_file_path(dir)
            
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
                os.rename(temp_path, validated_path)
                
                # Update cache
                self._config_cache[validated_path] = self.config.copy()
                self._config_mtime[validated_path] = datetime.now().timestamp()
                
        except (OSError, IOError, json.JSONEncodeError) as e:
            raise Exception(f"Failed to save config: {str(e)}")
    def load_config(self, dir):
        try:
            # Validate and normalize the file path
            validated_path = validate_file_path(dir)
            
            # Simplified loading without caching for now to debug
            if os.path.exists(validated_path):
                with open(validated_path, "r") as f:
                    self.config = json.load(f)
            else:
                # Create default config
                self.config = {"printers": []}
                self.save_config(validated_path)
                    
        except Exception as e:
            # Fallback to default config
            self.config = {"printers": []}
    
    def load_printer_profiles(self, profiles_dir):
        try:
            # Validate and normalize the file path
            validated_path = validate_file_path(profiles_dir)
            
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