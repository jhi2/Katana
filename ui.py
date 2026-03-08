import flask
from flask import *
from version import *
from configmanager import *
from validators import ValidationError, validate_printer_profile, validate_selection_data, validate_ip_address
import requests
import json as json_module
import os
import uuid
from werkzeug.utils import secure_filename
app = Flask(__name__)
config = ConfigManager()
removed_uploads = config.cleanup_orphan_uploads()
if removed_uploads > 0:
    print(f"Startup cleanup: removed {removed_uploads} orphan STL upload(s)")
with open("teapot.cfg", "r") as f:
    t = f.read().strip() == "True"
@app.route('/')
def load():
    if t:
        return abort(418) # See RFC 2324
    if config.check_config("config.json"):
        config.load_config("config.json")
        return render_template('index.html', version=v, page_title="Katana", project_name="Untitled")
    else:
        return render_template('welcomeflow.html', version=v, page_title="Katana", project_name="None")
    

@app.route('/welcome')
def welcome():
    return render_template('welcomeflow.html', version=v, page_title="Katana", project_name="None")

@app.route('/download_setup')
def download_setup():
    return render_template('download-setup.html', version=v, page_title="Katana - Download Configuration", project_name="None")

@app.route('/printer_setup')
def printer_setup():
    try:
        # Load prebuilt profiles
        config.load_printer_profiles("printers/printer-settings.json")
        prebuilt_profiles = config.get_printer_profiles()
        
        # Load saved config
        config.load_config("config.json")
        saved_printers = config.get_saved_printers()
        
        return render_template('printer-setup.html', 
                             version=v, 
                             page_title="Katana - Printer Setup",
                             profiles=prebuilt_profiles,
                             saved_printers=saved_printers,
                             project_name="None")
    except Exception as e:
        print(f"ERROR in printer_setup: {e}")
        # Return a simple error page to prevent loops
        return render_template('index.html', 
                          version=v, 
                          page_title="Katana - Error")

@app.route('/save_custom_printer', methods=['POST'])
def save_custom_printer():
    try:
        # Get and validate JSON data
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"})
        
        printer_data = request.get_json()
        if not printer_data:
            return jsonify({"success": False, "error": "No data provided"})
        
        # Validate the printer profile
        validated_data = validate_printer_profile(printer_data)
        
        # Load current config
        config.load_config("config.json")
        
        # Save the validated custom printer
        config.save_printer_to_config(validated_data)
        config.save_config("config.json")
        
        return jsonify({"success": True})
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": "Internal server error"})

@app.route('/save_printer_selection', methods=['POST'])
def save_printer_selection():
    try:
        # Get and validate JSON data
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"})
        
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"})
        
        # Validate selection data
        index, profile_type = validate_selection_data(data)
        
        # Get IP address if provided (for prebuilt profiles)
        ip_address = data.get('ip_address', '').strip()
        
        # Load current config and printer profiles
        config.load_config("config.json")
        config.load_printer_profiles("printers/printer-settings.json")
        
        # Get the actual profile data with bounds checking
        if profile_type == 'prebuilt':
            # Get prebuilt profile by index
            profiles = config.get_printer_profiles()
            if index >= len(profiles):
                return jsonify({"success": False, "error": "Invalid profile index"})
            profile_data = profiles[index].copy()  # Make a copy to modify
            
            # Update IP address if provided
            if ip_address:
                # Validate IP address
                validated_ip = validate_ip_address(ip_address)
                profile_data['ip_address'] = validated_ip
            else:
                profile_data['ip_address'] = ''
                
        elif profile_type == 'saved':
            # Get saved profile by index
            saved_printers = config.get_saved_printers()
            if index >= len(saved_printers):
                return jsonify({"success": False, "error": "Invalid saved profile index"})
            profile_data = saved_printers[index]['data']
        else:
            return jsonify({"success": False, "error": "Invalid profile type"})
        
        # Save the full profile data
        if "selected_printer" not in config.config:
            config.config["selected_printer"] = {}
        
        config.config["selected_printer"] = profile_data
        config.save_config("config.json")
        
        return jsonify({"success": True})
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)})
    except Exception as e:
        return jsonify({"success": False, "error": "Internal server error"})


@app.route('/api/config')
def get_current_config():
    try:
        config.load_config("config.json")
        return jsonify(config.config)
    except Exception as e:
        return jsonify({"success": False, "error": "Failed to load config"})


@app.route('/api/projects', methods=['GET'])
def list_projects():
    try:
        projects = config.list_projects()
        return jsonify(projects)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/projects', methods=['POST'])
def save_project():
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"})
        
        data = request.get_json()
        name = data.get('name', '').strip()
        project_data = data.get('data')
        
        if not name or not project_data:
            return jsonify({"success": False, "error": "Name and data are required"})
            
        success, result = config.save_project(name, project_data)
        if success:
            return jsonify({"success": True, "filename": result})
        else:
            return jsonify({"success": False, "error": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/projects/<filename>', methods=['GET'])
def load_project(filename):
    try:
        project_data = config.load_project(filename)
        if project_data:
            return jsonify(project_data)
        else:
            return jsonify({"success": False, "error": "Project not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/projects/<filename>', methods=['DELETE'])
def delete_project(filename):
    try:
        if config.delete_project(filename):
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Project not found or could not be deleted"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/set_project', methods=['POST'])
def set_project():
    try:
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"})
        
        data = request.get_json()
        name = data.get('name', 'Untitled')
        # This is just a UI session state, maybe save to config later if needed
        # For now, we'll just acknowledge it
        return jsonify({"success": True, "name": name})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/upload_model', methods=['POST'])
def upload_model():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part in request"})

        file = request.files['file']
        if not file or not file.filename:
            return jsonify({"success": False, "error": "No file selected"})

        filename = secure_filename(file.filename)
        if not filename.lower().endswith('.stl'):
            return jsonify({"success": False, "error": "Only .stl files are allowed"})

        base_name, ext = os.path.splitext(filename)
        unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext.lower()}"
        upload_dir = os.path.join(app.static_folder, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        abs_path = os.path.join(upload_dir, unique_name)
        file.save(abs_path)
        return jsonify({
            "success": True,
            "filename": unique_name,
            "url": f"/static/uploads/{unique_name}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": "Upload failed"})

@app.route('/download_config', methods=['POST'])
def download_config():
    try:
        # Get endpoint URL from request
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"})
        
        data = request.get_json()
        endpoint_url = data.get('endpoint_url', '').strip()
        
        if not endpoint_url:
            return jsonify({"success": False, "error": "No endpoint URL provided"})
        
        # Validate URL format
        if not endpoint_url.startswith(('http://', 'https://')):
            return jsonify({"success": False, "error": "Invalid URL format. Must start with http:// or https://"})
        
        # Try to download config
        try:
            download_url = endpoint_url
            if not download_url.endswith('/config.json'):
                if not download_url.endswith('/'):
                    download_url += '/'
                download_url += 'config.json'
                
            response = requests.get(download_url, timeout=10)
            response.raise_for_status()
            
            # Parse and validate the downloaded config
            downloaded_config = response.json()
            
            # Basic validation - check if it looks like a Katana config
            if not isinstance(downloaded_config, dict):
                return jsonify({"success": False, "error": "Invalid config format"})
            
            # Save the downloaded config
            config.config = downloaded_config
            config.save_config("config.json")
            
            return jsonify({
                "success": True, 
                "message": f"Config downloaded from {endpoint_url}",
                "config": downloaded_config
            })
            
        except requests.exceptions.RequestException as e:
            return jsonify({"success": False, "error": f"Failed to download: {str(e)}"})
        except json_module.JSONDecodeError:
            return jsonify({"success": False, "error": "Invalid JSON in downloaded config"})
            
    except Exception as e:
        return jsonify({"success": False, "error": "Internal server error"})


print("DO NOT RUN THIS SCRIPT DIRECTLY! USE main.py TO RUN KATANA!")
