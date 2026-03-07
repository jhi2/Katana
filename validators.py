"""
Input validation functions for Katana printer setup system
"""

import re
import os
import json
from typing import Dict, Any, List, Optional, Tuple

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

# JSON schema for printer profiles
PRINTER_PROFILE_SCHEMA = {
    "type": "object",
    "required": ["name", "manufacturer", "bed_size", "nozzle_size", "hotend_temp", "bed_temp", 
                 "speed_settings", "filament_diameter", "retraction", "gcode_start", "gcode_end"],
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "manufacturer": {"type": "string", "minLength": 1, "maxLength": 100},
        "bed_size": {
            "type": "array",
            "items": {"type": "number", "minimum": 50, "maximum": 1000},
            "minItems": 3,
            "maxItems": 3
        },
        "nozzle_size": {"type": "number", "minimum": 0.1, "maximum": 2.0},
        "filament_diameter": {"type": "number", "enum": [1.75, 2.85]},
        "hotend_temp": {
            "type": "object",
            "required": ["min", "max"],
            "properties": {
                "min": {"type": "number", "minimum": 0, "maximum": 500},
                "max": {"type": "number", "minimum": 0, "maximum": 500}
            }
        },
        "bed_temp": {
            "type": "object",
            "required": ["min", "max"],
            "properties": {
                "min": {"type": "number", "minimum": 0, "maximum": 500},
                "max": {"type": "number", "minimum": 0, "maximum": 500}
            }
        },
        "speed_settings": {
            "type": "object",
            "required": ["print_speed", "travel_speed", "infill_speed", "outer_wall_speed"],
            "properties": {
                "print_speed": {"type": "number", "minimum": 1, "maximum": 500},
                "travel_speed": {"type": "number", "minimum": 1, "maximum": 1000},
                "infill_speed": {"type": "number", "minimum": 1, "maximum": 500},
                "outer_wall_speed": {"type": "number", "minimum": 1, "maximum": 500}
            }
        },
        "retraction": {
            "type": "object",
            "required": ["enabled", "distance", "speed"],
            "properties": {
                "enabled": {"type": "boolean"},
                "distance": {"type": "number", "minimum": 0, "maximum": 50},
                "speed": {"type": "number", "minimum": 1, "maximum": 200}
            }
        },
        "gcode_start": {"type": "string", "maxLength": 10000},
        "gcode_end": {"type": "string", "maxLength": 10000}
    }
}

def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Simple JSON schema validation"""
    if not isinstance(data, dict):
        raise ValidationError("Data must be a dictionary")
    
    # Check required fields
    if "required" in schema:
        for field in schema["required"]:
            if field not in data:
                raise ValidationError(f"Missing required field: {field}")
    
    # Check properties
    if "properties" in schema:
        for field, field_schema in schema["properties"].items():
            if field in data:
                _validate_field(data[field], field_schema, field)
    
    return True

def _validate_field(value: Any, schema: Any, field_name: str):
    """Validate a single field against its schema"""
    if isinstance(schema, dict):
        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "string":
                if not isinstance(value, str):
                    raise ValidationError(f"{field_name} must be a string")
                if "minLength" in schema and len(value) < schema["minLength"]:
                    raise ValidationError(f"{field_name} must be at least {schema['minLength']} characters")
                if "maxLength" in schema and len(value) > schema["maxLength"]:
                    raise ValidationError(f"{field_name} must be at most {schema['maxLength']} characters")
            elif expected_type == "number":
                if not isinstance(value, (int, float)):
                    raise ValidationError(f"{field_name} must be a number")
                if "minimum" in schema and value < schema["minimum"]:
                    raise ValidationError(f"{field_name} must be at least {schema['minimum']}")
                if "maximum" in schema and value > schema["maximum"]:
                    raise ValidationError(f"{field_name} must be at most {schema['maximum']}")
            elif expected_type == "boolean":
                if not isinstance(value, bool):
                    raise ValidationError(f"{field_name} must be a boolean")
            elif expected_type == "array":
                if not isinstance(value, list):
                    raise ValidationError(f"{field_name} must be an array")
                if "minItems" in schema and len(value) < schema["minItems"]:
                    raise ValidationError(f"{field_name} must have at least {schema['minItems']} items")
                if "maxItems" in schema and len(value) > schema["maxItems"]:
                    raise ValidationError(f"{field_name} must have at most {schema['maxItems']} items")
                if "items" in schema:
                    for i, item in enumerate(value):
                        _validate_field(item, schema["items"], f"{field_name}[{i}]")
            elif expected_type == "object":
                if not isinstance(value, dict):
                    raise ValidationError(f"{field_name} must be an object")
                validate_json_schema(value, schema)
    elif isinstance(schema, list):
        # Enum validation
        if value not in schema:
            raise ValidationError(f"{field_name} must be one of: {', '.join(map(str, schema))}")

def validate_printer_profiles_file(file_path: str) -> bool:
    """Validate the printer profiles JSON file structure"""
    try:
        if not os.path.exists(file_path):
            raise ValidationError(f"File not found: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            raise ValidationError("Root element must be an object")
        
        if "profiles" not in data:
            raise ValidationError("Missing 'profiles' field")
        
        profiles = data["profiles"]
        if not isinstance(profiles, list):
            raise ValidationError("'profiles' must be an array")
        
        # Validate each profile
        for i, profile in enumerate(profiles):
            try:
                validate_json_schema(profile, PRINTER_PROFILE_SCHEMA)
            except ValidationError as e:
                raise ValidationError(f"Profile {i}: {str(e)}")
        
        return True
    
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        if isinstance(e, ValidationError):
            raise
        raise ValidationError(f"Failed to validate file: {str(e)}")

def validate_printer_name(name: str) -> str:
    """Validate printer name"""
    if not name or not isinstance(name, str):
        raise ValidationError("Printer name is required")
    
    name = name.strip()
    if len(name) < 1 or len(name) > 100:
        raise ValidationError("Printer name must be between 1 and 100 characters")
    
    # Allow letters, numbers, spaces, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', name):
        raise ValidationError("Printer name contains invalid characters")
    
    return name

def validate_manufacturer(manufacturer: str) -> str:
    """Validate manufacturer name"""
    if not manufacturer or not isinstance(manufacturer, str):
        raise ValidationError("Manufacturer is required")
    
    manufacturer = manufacturer.strip()
    if len(manufacturer) < 1 or len(manufacturer) > 100:
        raise ValidationError("Manufacturer must be between 1 and 100 characters")
    
    # Allow letters, numbers, spaces, hyphens, and underscores
    if not re.match(r'^[a-zA-Z0-9\s\-_]+$', manufacturer):
        raise ValidationError("Manufacturer contains invalid characters")
    
    return manufacturer

def validate_bed_dimensions(width: Any, depth: Any, height: Any) -> Tuple[int, int, int]:
    """Validate bed dimensions"""
    try:
        width = int(float(width))
        depth = int(float(depth))
        height = int(float(height))
    except (ValueError, TypeError):
        raise ValidationError("Bed dimensions must be valid numbers")
    
    if width < 50 or width > 1000:
        raise ValidationError("Bed width must be between 50 and 1000mm")
    
    if depth < 50 or depth > 1000:
        raise ValidationError("Bed depth must be between 50 and 1000mm")
    
    if height < 50 or height > 1000:
        raise ValidationError("Bed height must be between 50 and 1000mm")
    
    return width, depth, height

def validate_nozzle_size(nozzle_size: Any) -> float:
    """Validate nozzle size"""
    try:
        nozzle_size = float(nozzle_size)
    except (ValueError, TypeError):
        raise ValidationError("Nozzle size must be a valid number")
    
    if nozzle_size < 0.1 or nozzle_size > 2.0:
        raise ValidationError("Nozzle size must be between 0.1 and 2.0mm")
    
    return nozzle_size

def validate_filament_diameter(filament_diameter: Any) -> float:
    """Validate filament diameter"""
    try:
        filament_diameter = float(filament_diameter)
    except (ValueError, TypeError):
        raise ValidationError("Filament diameter must be a valid number")
    
    valid_diameters = [1.75, 2.85]
    if filament_diameter not in valid_diameters:
        raise ValidationError(f"Filament diameter must be one of: {', '.join(map(str, valid_diameters))}mm")
    
    return filament_diameter

def validate_temperature_range(min_temp: Any, max_temp: Any) -> Tuple[int, int]:
    """Validate temperature range"""
    try:
        min_temp = int(float(min_temp))
        max_temp = int(float(max_temp))
    except (ValueError, TypeError):
        raise ValidationError("Temperatures must be valid numbers")
    
    if min_temp < 0 or min_temp > 500:
        raise ValidationError("Minimum temperature must be between 0 and 500°C")
    
    if max_temp < 0 or max_temp > 500:
        raise ValidationError("Maximum temperature must be between 0 and 500°C")
    
    if max_temp <= min_temp:
        raise ValidationError("Maximum temperature must be greater than minimum temperature")
    
    return min_temp, max_temp

def validate_gcode(gcode: str) -> str:
    """Validate G-code string for security"""
    if not isinstance(gcode, str):
        raise ValidationError("G-code must be a string")
    
    # Remove any potentially dangerous characters
    # Allow only G-code commands, numbers, letters, spaces, and basic punctuation
    gcode = re.sub(r'[^\w\s\-\.\;\:\n\r\t\{\}\(\)\[\]\+\*\/\%\&\|\!\?\~\^]', '', gcode)
    
    # Limit length to prevent injection attacks
    if len(gcode) > 10000:
        raise ValidationError("G-code is too long")
    
    return gcode.strip()

def validate_printer_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate complete printer profile"""
    if not isinstance(profile_data, dict):
        raise ValidationError("Profile data must be a dictionary")
    
    validated = {}
    
    # Validate required fields
    validated['name'] = validate_printer_name(profile_data.get('name', ''))
    validated['manufacturer'] = validate_manufacturer(profile_data.get('manufacturer', ''))
    
    # Validate bed dimensions
    bed_size = profile_data.get('bed_size', [])
    if not isinstance(bed_size, list) or len(bed_size) != 3:
        raise ValidationError("Bed size must be an array of 3 numbers [width, depth, height]")
    
    width, depth, height = validate_bed_dimensions(bed_size[0], bed_size[1], bed_size[2])
    validated['bed_size'] = [width, depth, height]
    
    # Validate nozzle size
    validated['nozzle_size'] = validate_nozzle_size(profile_data.get('nozzle_size', 0.4))
    
    # Validate filament diameter
    validated['filament_diameter'] = validate_filament_diameter(
        profile_data.get('filament_diameter', 1.75)
    )
    
    # Validate temperature ranges
    hotend_temp = profile_data.get('hotend_temp', {})
    if not isinstance(hotend_temp, dict):
        raise ValidationError("Hotend temperature must be an object")
    
    hotend_min, hotend_max = validate_temperature_range(
        hotend_temp.get('min', 180),
        hotend_temp.get('max', 260)
    )
    validated['hotend_temp'] = {'min': hotend_min, 'max': hotend_max}
    
    bed_temp = profile_data.get('bed_temp', {})
    if not isinstance(bed_temp, dict):
        raise ValidationError("Bed temperature must be an object")
    
    bed_min, bed_max = validate_temperature_range(
        bed_temp.get('min', 0),
        bed_temp.get('max', 100)
    )
    validated['bed_temp'] = {'min': bed_min, 'max': bed_max}
    
    # Validate speed settings
    speed_settings = profile_data.get('speed_settings', {})
    if not isinstance(speed_settings, dict):
        raise ValidationError("Speed settings must be an object")
    
    validated['speed_settings'] = {
        'print_speed': max(1, min(500, int(float(speed_settings.get('print_speed', 50))))),
        'travel_speed': max(1, min(1000, int(float(speed_settings.get('travel_speed', 150))))),
        'infill_speed': max(1, min(500, int(float(speed_settings.get('infill_speed', 60))))),
        'outer_wall_speed': max(1, min(500, int(float(speed_settings.get('outer_wall_speed', 40)))))
    }
    
    # Validate retraction settings
    retraction = profile_data.get('retraction', {})
    if not isinstance(retraction, dict):
        raise ValidationError("Retraction settings must be an object")
    
    validated['retraction'] = {
        'enabled': bool(retraction.get('enabled', True)),
        'distance': max(0, min(50, float(retraction.get('distance', 5)))),
        'speed': max(1, min(200, int(float(retraction.get('speed', 45)))))
    }
    
    # Validate G-code
    validated['gcode_start'] = validate_gcode(profile_data.get('gcode_start', ''))
    validated['gcode_end'] = validate_gcode(profile_data.get('gcode_end', ''))
    
    return validated

def validate_selection_data(data: Dict[str, Any]) -> Tuple[int, str]:
    """Validate printer selection data"""
    if not isinstance(data, dict):
        raise ValidationError("Selection data must be a dictionary")
    
    # Validate index
    index = data.get('index')
    if not isinstance(index, int) or index < 0:
        raise ValidationError("Index must be a non-negative integer")
    
    # Validate type
    profile_type = data.get('type')
    if profile_type not in ['prebuilt', 'saved']:
        raise ValidationError("Type must be 'prebuilt' or 'saved'")
    
    return index, profile_type

def validate_file_path(file_path: str, base_dir: str = None) -> str:
    """Validate and sanitize file path to prevent path traversal"""
    if not isinstance(file_path, str):
        raise ValidationError("File path must be a string")
    
    # Normalize the path
    file_path = os.path.normpath(file_path)
    
    # Check for path traversal attempts
    if '..' in file_path or file_path.startswith('/'):
        raise ValidationError("Invalid file path")
    
    # If base directory is provided, ensure the path is within it
    if base_dir:
        base_dir = os.path.normpath(base_dir)
        full_path = os.path.join(base_dir, file_path)
        full_path = os.path.normpath(full_path)
        
        if not full_path.startswith(base_dir):
            raise ValidationError("File path is outside allowed directory")
        
        return full_path
    
    return file_path
