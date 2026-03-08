import flask
from flask import *
from version import *
from configmanager import *
from validators import ValidationError, validate_printer_profile, validate_selection_data, validate_ip_address
import requests
import json as json_module
import os
import uuid
import zipfile
import math
import xml.etree.ElementTree as ET
import shutil
from werkzeug.utils import secure_filename
app = Flask(__name__)
config = ConfigManager()
with open("teapot.cfg", "r") as f:
    t = f.read().strip() == "True"

def seed_demo_project():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "demo", "demo_block.json")
        if not os.path.exists(template_path):
            return
        projects_dir = os.path.join(base_dir, "projects")
        os.makedirs(projects_dir, exist_ok=True)
        target_path = os.path.join(projects_dir, "Demo Block.json")
        if not os.path.exists(target_path):
            shutil.copy2(template_path, target_path)
            return

        # One-time migration for older demo project URLs.
        with open(target_path, "r") as f:
            existing = json_module.load(f)
        model_block = existing.get("models", {})
        models = model_block.get("models", []) if isinstance(model_block, dict) else []
        needs_migration = any(
            isinstance(m, dict) and m.get("url", "").startswith("/static/uploads/block_demo")
            for m in models
        )
        if needs_migration:
            shutil.copy2(template_path, target_path)
    except Exception as e:
        print(f"Failed to seed demo project: {e}")

seed_demo_project()

UNIT_TO_MM = {
    "micron": 0.001,
    "millimeter": 1.0,
    "centimeter": 10.0,
    "inch": 25.4,
    "foot": 304.8,
    "meter": 1000.0
}

def _compute_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return nx / length, ny / length, nz / length

def _write_ascii_stl(path, solid_name, vertices, triangles, scale):
    with open(path, "w") as f:
        f.write(f"solid {solid_name}\n")
        for i1, i2, i3 in triangles:
            a = (vertices[i1][0] * scale, vertices[i1][1] * scale, vertices[i1][2] * scale)
            b = (vertices[i2][0] * scale, vertices[i2][1] * scale, vertices[i2][2] * scale)
            c = (vertices[i3][0] * scale, vertices[i3][1] * scale, vertices[i3][2] * scale)
            nx, ny, nz = _compute_normal(a, b, c)
            f.write(f"  facet normal {nx} {ny} {nz}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {a[0]} {a[1]} {a[2]}\n")
            f.write(f"      vertex {b[0]} {b[1]} {b[2]}\n")
            f.write(f"      vertex {c[0]} {c[1]} {c[2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {solid_name}\n")

def _extract_3mf_models(file_storage, upload_dir, base_name):
    file_storage.stream.seek(0)
    generated = []
    with zipfile.ZipFile(file_storage.stream) as zf:
        model_entries = [name for name in zf.namelist() if name.lower().endswith(".model")]
        if not model_entries:
            raise ValueError("No .model payload found in 3MF file")

        for model_entry in model_entries:
            root = ET.fromstring(zf.read(model_entry))
            ns_uri = root.tag[root.tag.find("{") + 1:root.tag.find("}")]
            ns = {"m": ns_uri}
            scale = UNIT_TO_MM.get(root.attrib.get("unit", "millimeter"), 1.0)

            resources = root.find("m:resources", ns)
            if resources is None:
                continue

            for obj in resources.findall("m:object", ns):
                mesh = obj.find("m:mesh", ns)
                if mesh is None:
                    continue

                vertices_tag = mesh.find("m:vertices", ns)
                triangles_tag = mesh.find("m:triangles", ns)
                if vertices_tag is None or triangles_tag is None:
                    continue

                vertices = []
                for vtx in vertices_tag.findall("m:vertex", ns):
                    vertices.append((
                        float(vtx.attrib.get("x", 0.0)),
                        float(vtx.attrib.get("y", 0.0)),
                        float(vtx.attrib.get("z", 0.0))
                    ))

                triangles = []
                for tri in triangles_tag.findall("m:triangle", ns):
                    i1 = int(tri.attrib.get("v1", 0))
                    i2 = int(tri.attrib.get("v2", 0))
                    i3 = int(tri.attrib.get("v3", 0))
                    if i1 < len(vertices) and i2 < len(vertices) and i3 < len(vertices):
                        triangles.append((i1, i2, i3))

                if not vertices or not triangles:
                    continue

                obj_id = obj.attrib.get("id", "model")
                out_name = secure_filename(f"{base_name}_{obj_id}_{uuid.uuid4().hex[:8]}.stl")
                out_path = os.path.join(upload_dir, out_name)
                _write_ascii_stl(out_path, f"{base_name}_{obj_id}", vertices, triangles, scale)
                generated.append({
                    "filename": out_name,
                    "url": f"/static/uploads/{out_name}"
                })
    return generated
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

@app.route('/demo/block.stl')
def demo_block_stl():
    return send_file("block.stl")

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
        previous_filename = data.get('previous_filename')
        
        if not name or not project_data:
            return jsonify({"success": False, "error": "Name and data are required"})
            
        success, result = config.save_project(name, project_data, previous_filename=previous_filename)
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
        lower_name = filename.lower()
        if not (lower_name.endswith('.stl') or lower_name.endswith('.3mf')):
            return jsonify({"success": False, "error": "Only .stl and .3mf files are allowed"})

        upload_dir = os.path.join(app.static_folder, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        if lower_name.endswith('.stl'):
            base_name, ext = os.path.splitext(filename)
            unique_name = f"{base_name}_{uuid.uuid4().hex[:8]}{ext.lower()}"
            abs_path = os.path.join(upload_dir, unique_name)
            file.save(abs_path)
            return jsonify({
                "success": True,
                "filename": unique_name,
                "url": f"/static/uploads/{unique_name}",
                "models": [{"filename": unique_name, "url": f"/static/uploads/{unique_name}"}]
            })

        base_name, _ = os.path.splitext(filename)
        models = _extract_3mf_models(file, upload_dir, secure_filename(base_name) or "model")
        if not models:
            return jsonify({"success": False, "error": "No mesh models found in 3MF file"})
        return jsonify({
            "success": True,
            "source": "3mf",
            "models": models
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
