import os
import json
import math
import struct
from werkzeug.utils import secure_filename


DEFAULT_PLATE_PADDING_MM = 50.0


def parse_ini_file(ini_path):
    data = {}
    with open(ini_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def load_project_file(project_path):
    with open(project_path, "r") as f:
        return json.load(f)


def _coerce_float(value, fallback):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _safe_slug(text, fallback):
    safe = secure_filename(str(text or "").strip())
    return safe or fallback


def _resolve_model_url_to_path(model_url, base_dir):
    if not model_url:
        return None
    url = str(model_url).strip()
    if not url:
        return None

    if url.startswith("/static/"):
        rel = url.lstrip("/")
        return os.path.join(base_dir, rel)

    if url.startswith("/demo/"):
        # Current app route maps /demo/block.stl -> ./block.stl
        filename = os.path.basename(url)
        return os.path.join(base_dir, filename)

    if os.path.isabs(url):
        return url

    return os.path.join(base_dir, url)


def _infer_plate_index(model, plate_count, plate_width, padding_mm):
    if plate_count <= 1:
        return 0
    pos = model.get("position", {}) if isinstance(model, dict) else {}
    x = _coerce_float(pos.get("x", 0), 0.0)
    span = max(1.0, float(plate_width) + float(padding_mm))
    idx = int(round(x / span))
    return max(0, min(plate_count - 1, idx))


def _rotate_xyz(vx, vy, vz, rx, ry, rz):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)

    # X
    y1 = vy * cx - vz * sx
    z1 = vy * sx + vz * cx
    x1 = vx

    # Y
    x2 = x1 * cy + z1 * sy
    z2 = -x1 * sy + z1 * cy
    y2 = y1

    # Z
    x3 = x2 * cz - y2 * sz
    y3 = x2 * sz + y2 * cz
    z3 = z2
    return x3, y3, z3


def _compute_normal(a, b, c):
    ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / ln, ny / ln, nz / ln)


def _read_stl_triangles(stl_path):
    with open(stl_path, "rb") as f:
        blob = f.read()

    # Heuristic: binary STL has count at bytes 80..84 and exact size.
    if len(blob) >= 84:
        tri_count = struct.unpack("<I", blob[80:84])[0]
        expected = 84 + tri_count * 50
        if expected == len(blob):
            triangles = []
            off = 84
            for _ in range(tri_count):
                # skip normal
                off += 12
                v1 = struct.unpack("<fff", blob[off:off + 12]); off += 12
                v2 = struct.unpack("<fff", blob[off:off + 12]); off += 12
                v3 = struct.unpack("<fff", blob[off:off + 12]); off += 12
                off += 2  # attribute byte count
                triangles.append((v1, v2, v3))
            return triangles

    # ASCII fallback
    text = blob.decode("utf-8", errors="ignore")
    triangles = []
    verts = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.lower().startswith("vertex "):
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            verts.append((float(parts[1]), float(parts[2]), float(parts[3])))
        except ValueError:
            continue
        if len(verts) == 3:
            triangles.append((verts[0], verts[1], verts[2]))
            verts = []
    return triangles


def _write_ascii_stl(path, solid_name, triangles):
    with open(path, "w") as f:
        f.write(f"solid {solid_name}\n")
        for tri in triangles:
            a, b, c = tri
            n = _compute_normal(a, b, c)
            f.write(f"  facet normal {n[0]} {n[1]} {n[2]}\n")
            f.write("    outer loop\n")
            f.write(f"      vertex {a[0]} {a[1]} {a[2]}\n")
            f.write(f"      vertex {b[0]} {b[1]} {b[2]}\n")
            f.write(f"      vertex {c[0]} {c[1]} {c[2]}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write(f"endsolid {solid_name}\n")


def _bake_model_to_stl(model, source_model_path, baked_dir, project_slug, plate_index, model_index, plate_width, padding_mm):
    pos = model.get("position", {}) if isinstance(model, dict) else {}
    rot = model.get("rotation", {}) if isinstance(model, dict) else {}
    scale = model.get("scale", {}) if isinstance(model, dict) else {}

    span = max(1.0, float(plate_width) + float(padding_mm))
    x_world = _coerce_float(pos.get("x", 0), 0.0)
    y_world = _coerce_float(pos.get("y", 0), 0.0)
    z_world = _coerce_float(pos.get("z", 0), 0.0)

    # Convert world x to plate-local x so each plate command slices independently.
    x_local = x_world - (plate_index * span)

    # Katana scene is Y-up (Three.js), OpenSCAD is Z-up.
    tx = x_local
    ty = z_world
    tz = y_world

    rx = _coerce_float(rot.get("x", 0), 0.0)
    ry = _coerce_float(rot.get("y", 0), 0.0)
    rz = _coerce_float(rot.get("z", 0), 0.0)

    sx = _coerce_float(scale.get("x", 1), 1.0)  # three.js X
    sy = _coerce_float(scale.get("y", 1), 1.0)  # three.js Y (up)
    sz = _coerce_float(scale.get("z", 1), 1.0)  # three.js Z

    os.makedirs(baked_dir, exist_ok=True)
    model_name = _safe_slug(model.get("name", f"model_{model_index + 1}"), f"model_{model_index + 1}")
    stl_name = f"{project_slug}_plate_{plate_index + 1}_{model_index + 1}_{model_name}.stl"
    stl_path = os.path.join(baked_dir, stl_name)

    if not str(source_model_path).lower().endswith(".stl"):
        raise ValueError(f"Baking currently supports STL sources only: {source_model_path}")

    src_tris = _read_stl_triangles(source_model_path)
    baked_tris = []
    for tri in src_tris:
        new_tri = []
        for vx, vy, vz in tri:
            # Apply Three.js local transforms.
            lx = vx * sx
            ly = vy * sy
            lz = vz * sz
            rxv, ryv, rzv = _rotate_xyz(lx, ly, lz, rx, ry, rz)
            wx = rxv + x_local
            wy = ryv + y_world
            wz = rzv + z_world

            # Convert to printer coords: Three.js Y-up -> printer Z-up.
            px = wx
            py = wz
            pz = wy
            new_tri.append((px, py, pz))
        baked_tris.append((new_tri[0], new_tri[1], new_tri[2]))

    _write_ascii_stl(stl_path, f"{project_slug}_plate_{plate_index + 1}_{model_index + 1}", baked_tris)
    return stl_path


def build_print3r_plate_commands(project_ini_path, project_json_path, slicer="slic3r", bake_models=True):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ini_data = parse_ini_file(project_ini_path)
    project = load_project_file(project_json_path)

    profile_name = os.path.splitext(os.path.basename(project_ini_path))[0]
    project_name = project.get("name", os.path.splitext(os.path.basename(project_json_path))[0])
    project_slug = _safe_slug(project_name, "project")

    model_block = project.get("models", {})
    models = model_block.get("models", []) if isinstance(model_block, dict) else []
    plate_count = int(model_block.get("plateCount", 1)) if isinstance(model_block, dict) else 1
    plate_count = max(1, plate_count)

    machine_width = _coerce_float(ini_data.get("machine_width", 220), 220.0)
    machine_depth = _coerce_float(ini_data.get("machine_depth", 220), 220.0)
    plate_width = max(machine_width, machine_depth)

    grouped = {i: [] for i in range(plate_count)}
    for model in models:
        if not isinstance(model, dict):
            continue
        model_path = _resolve_model_url_to_path(model.get("url", ""), base_dir)
        if not model_path:
            continue
        plate_idx = _infer_plate_index(model, plate_count, plate_width, DEFAULT_PLATE_PADDING_MM)
        grouped[plate_idx].append({
            "model": model,
            "source_path": model_path
        })

    commands = []
    baked_root = os.path.join(base_dir, "baked", project_slug)
    gcode_root = os.path.join(base_dir, "gcode")
    os.makedirs(gcode_root, exist_ok=True)
    for plate_idx in range(plate_count):
        plate_entries = grouped.get(plate_idx, [])
        if not plate_entries:
            continue

        plate_models = []
        plate_baked_dir = os.path.join(baked_root, f"plate_{plate_idx + 1}")
        for model_idx, entry in enumerate(plate_entries):
            src = entry["source_path"]
            if bake_models:
                baked_stl = _bake_model_to_stl(
                    model=entry["model"],
                    source_model_path=src,
                    baked_dir=plate_baked_dir,
                    project_slug=project_slug,
                    plate_index=plate_idx,
                    model_index=model_idx,
                    plate_width=plate_width,
                    padding_mm=DEFAULT_PLATE_PADDING_MM
                )
                plate_models.append(baked_stl)
            else:
                plate_models.append(src)

        if plate_count == 1:
            out_name = f"{project_slug}.gcode"
        else:
            out_name = f"{project_slug}_plate_{plate_idx + 1}.gcode"
        out_path = os.path.join(gcode_root, out_name)
        argv = ["print3r", f"--printer={profile_name}"]
        if slicer:
            argv.append(f"--slicer={slicer}")
        argv.extend(["-o", out_path, "slice", *plate_models])

        commands.append({
            "plate_index": plate_idx,
            "output_gcode": out_path,
            "argv": argv,
            "models": plate_models,
            "baked": bool(bake_models),
            "baked_dir": plate_baked_dir if bake_models else ""
        })

    return {
        "profile_name": profile_name,
        "project_name": project_name,
        "project_file": project_json_path,
        "ini_file": project_ini_path,
        "commands": commands
    }
