import subprocess
import time
import os
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

        return {
            "ui": {
                "images": images,
                "mesh_audit_carousel": [{"labels": labels}],
            }
        }

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time()
