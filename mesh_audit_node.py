import subprocess
import sys
import time
import os
import json
from uuid import uuid4
import folder_paths

# Path to the agnirt binary bundled with this plugin
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
if sys.platform == "win32":
    AGNIRT_DIR = os.path.join(PLUGIN_DIR, "bin", "win-x64")
    AGNIRT_BIN = os.path.join(AGNIRT_DIR, "agnirt.exe")
else:
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
        # Resolve relative paths — check output directory first, then input directory
        if not os.path.isabs(file_path):
            output_candidate = os.path.join(folder_paths.get_output_directory(), file_path)
            input_candidate = os.path.join(folder_paths.get_input_directory(), file_path)
            if os.path.isfile(output_candidate):
                file_path = output_candidate
            else:
                file_path = input_candidate

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

        print("[MeshAudit] Starting agnirt...")
        proc = subprocess.Popen(
            [
                AGNIRT_BIN, "vulkan", file_path,
                "-headless",
                "-shading-mode", "all",
                "--camera", "perspective", "front", "right", "left",
                "-env", "../../assets/sunny_rose_garden_4k.exr",
                "-o", output_base,
            ],
            cwd=AGNIRT_DIR,   # agnirt reads assets/ relative to cwd
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout_lines = []
        for line in proc.stdout:
            line = line.rstrip()
            stdout_lines.append(line)
            print(f"[agnirt] {line}", flush=True)

        proc.wait()
        stderr_out = proc.stderr.read()

        if proc.returncode != 0:
            raise RuntimeError(
                f"agnirt failed (rc={proc.returncode}):\n{stderr_out[-1000:]}"
            )

        # Expose result-like interface for downstream code
        class _Result:
            stdout = "\n".join(stdout_lines)
        result = _Result()

        # Build image list + carousel labels in camera-outer, mode-inner order
        images = []
        labels = []
        for mode in MODES:
            for cam in CAMERAS:
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

        # Try multiple possible locations for audit_log
        possible_temps = [
            temp_dir,
            "/home/krishnan/ai_lab/apps/ComfyUI/temp",
            os.path.expanduser("~/ai_lab/apps/ComfyUI/temp"),
        ]

        audit_log_path = None
        for search_dir in possible_temps:
            if os.path.isdir(search_dir):
                audit_logs = glob.glob(os.path.join(search_dir, "audit_log_*.json"))
                if audit_logs:
                    audit_log_path = max(audit_logs, key=os.path.getctime)
                    break

        if audit_log_path:
            print(f"[MeshAudit] Found audit log: {audit_log_path}")
            asset_stats = _parse_audit_log(audit_log_path, len(MODES) * len(CAMERAS))
            if asset_stats:
                print(f"[MeshAudit] Parsed stats: {asset_stats['scene']['name']}")
        else:
            print(f"[MeshAudit] Could not find audit_log in any temp directory")

        response = {
            "ui": {
                "images": images,
                "mesh_audit_carousel": [{"labels": labels}],
            }
        }

        # Add asset_stats if parsing succeeded
        if asset_stats:
            response["ui"]["asset_stats"] = [asset_stats]

        return response

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()
