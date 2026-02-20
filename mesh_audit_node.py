import subprocess
import time
import os
import json
from uuid import uuid4
import folder_paths

# Path to the agnirt binary bundled with this plugin
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
AGNIRT_DIR = os.path.join(PLUGIN_DIR, "bin", "linux-x64")
AGNIRT_BIN = os.path.join(AGNIRT_DIR, "agnirt")

# agnirt output segment names (must match what the binary emits)
CAMERAS = ["perspective", "front", "right", "left"]
MODES   = ["pathtracing", "wireframe", "geometry-analysis", "sliver-triangles"]

# Human-readable display labels for the carousel
CAMERA_DISPLAY = {
    "perspective": "Perspective",
    "front":       "Front",
    "right":       "Right",
    "left":        "Left",
}
MODE_DISPLAY = {
    "pathtracing":        "Path Trace",
    "wireframe":          "Wireframe",
    "geometry-analysis":  "Geo Analysis",
    "sliver-triangles":   "Sliver Tri",
}


def _parse_audit_log(log_path, total_faces):
    """
    Parse audit_log.json and extract mesh statistics.

    Args:
        log_path: Path to audit_log.json file
        total_faces: Total face count (used to calculate degenerate % if needed)

    Returns:
        Dict with keys: scene, geometry, quality_metrics
        Returns None if file not found or parse error
    """
    try:
        with open(log_path, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not parse audit_log.json: {e}")
        return None

    try:
        # Extract scene metadata
        asset_name = data.get("asset", {}).get("name", "Unknown")
        timestamp = data.get("asset", {}).get("timestamp", "N/A")

        # Extract geometry stats
        scene = data.get("scene_stats", {})
        edge_count = scene.get("edge_count", 0)
        face_count = scene.get("face_count", 0)
        vertex_count = scene.get("vertex_count", 0)

        # Extract validation metrics
        validation = data.get("validation", {})
        degen_count = validation.get("degenerate_triangles", 0)
        inverted_count = validation.get("inverted_triangles", 0)
        sliver_data = validation.get("sliver_triangles", {})
        sliver_pct = sliver_data.get("percentage", 0.0) if isinstance(sliver_data, dict) else 0.0

        # Calculate percentages (avoid division by zero)
        degen_pct = (degen_count / face_count * 100) if face_count > 0 else 0.0
        inverted_pct = (inverted_count / face_count * 100) if face_count > 0 else 0.0

        return {
            "scene": {
                "name": asset_name,
                "timestamp": timestamp
            },
            "geometry": {
                "edge_count": edge_count,
                "face_count": face_count,
                "vertex_count": vertex_count
            },
            "quality_metrics": {
                "degenerate_triangles_pct": round(degen_pct, 2),
                "sliver_triangles_pct": round(sliver_pct, 2),
                "inverted_triangles_pct": round(inverted_pct, 2)
            }
        }
    except Exception as e:
        print(f"Warning: Error extracting stats from audit_log.json: {e}")
        return None


class PulseMeshAudit:
    CATEGORY = "Pulse/MeshAudit"
    RETURN_TYPES = ()
    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "file_path": ("STRING", {"default": ""}),
            }
        }

    FUNCTION = "execute"

    def execute(self, file_path):
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Mesh file not found: {file_path}")

        # Output base: agnirt appends _{mode}_{camera}.png automatically
        run_id = str(uuid4())[:8]
        temp_dir = folder_paths.get_temp_directory()
        output_base = os.path.join(temp_dir, f"ma_{run_id}.png")

        # Need lib dir on LD_LIBRARY_PATH for libcrt_vulkan.so
        env = os.environ.copy()
        prev_ldpath = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{AGNIRT_DIR}:{prev_ldpath}" if prev_ldpath else AGNIRT_DIR

        result = subprocess.run(
            [
                AGNIRT_BIN, "vulkan", file_path,
                "-headless",
                "-shading-mode", "all",
                "--camera", "perspective", "front", "right", "left",
                "-o", output_base,
            ],
            cwd=AGNIRT_DIR,   # agnirt reads assets/ relative to cwd
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"agnirt failed (rc={result.returncode}):\n{result.stderr[-1000:]}"
            )

        # Build image list + carousel labels in camera-outer, mode-inner order
        images = []
        labels = []
        for cam in CAMERAS:
            for mode in MODES:
                filename = f"ma_{run_id}_{mode}_{cam}.png"
                full_path = os.path.join(temp_dir, filename)
                if not os.path.isfile(full_path):
                    raise FileNotFoundError(
                        f"Expected agnirt output missing: {filename}\n"
                        f"agnirt stdout: {result.stdout[-500:]}"
                    )
                images.append({"filename": filename, "subfolder": "", "type": "temp"})
                labels.append(f"{CAMERA_DISPLAY[cam]} • {MODE_DISPLAY[mode]}")

        # Locate and parse audit_log.json if available
        # agnirt creates audit_log_<name>_<timestamp>.json, find the latest one
        asset_stats = None
        import glob
        audit_logs = glob.glob(os.path.join(temp_dir, "audit_log_*.json"))
        print(f"[MeshAudit] Temp dir: {temp_dir}")
        print(f"[MeshAudit] Found audit logs: {audit_logs}")
        if audit_logs:
            # Use the most recently created audit_log
            audit_log_path = max(audit_logs, key=os.path.getctime)
            print(f"[MeshAudit] Parsing audit log: {audit_log_path}")
            asset_stats = _parse_audit_log(audit_log_path, len(MODES) * len(CAMERAS))
            print(f"[MeshAudit] Asset stats result: {asset_stats}")
        else:
            print(f"[MeshAudit] Note: audit_log_*.json not found in {temp_dir}")
            # List all files in temp dir for debugging
            all_files = os.listdir(temp_dir)
            print(f"[MeshAudit] Files in temp_dir: {all_files[:10]}")

        response = {
            "ui": {
                "images": images,
                "mesh_audit_carousel": [{"labels": labels}],
            }
        }

        # Add asset_stats if parsing succeeded
        if asset_stats:
            response["ui"]["asset_stats"] = asset_stats

        return response

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()
