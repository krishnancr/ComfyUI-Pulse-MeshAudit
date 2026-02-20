# Real agnirt Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the placeholder subprocess and pre-baked image copying in `mesh_audit_node.py` with a real `agnirt` render call that produces 16 PNGs on demand.

**Architecture:** `execute()` runs `bin/linux-x64/agnirt vulkan <file_path> -headless -shading-mode all --camera perspective front right left -o <temp_dir>/ma_<run_id>.png`, which writes 16 files named `ma_<run_id>_<mode>_<camera>.png` directly into ComfyUI's temp dir. No file-copy step needed — the outputs land exactly where ComfyUI expects them.

**Tech Stack:** Python stdlib (`subprocess`, `os`, `uuid`), ComfyUI `folder_paths`, existing `agnirt` binary at `bin/linux-x64/agnirt`.

---

## Pre-flight verification (already done — recorded here for reference)

Test command run against `BrainStem.glb`:

```bash
cd bin/linux-x64
LD_LIBRARY_PATH=$(pwd) ./agnirt vulkan /path/to/file.glb \
  -headless -shading-mode all \
  --camera perspective front right left \
  -o /tmp/agnirt_test/out.png
```

Produces 16 files: `out_<mode>_<camera>.png` where
- mode ∈ `pathtracing wireframe geometry-analysis sliver-triangles`
- camera ∈ `perspective front right left`

Completes in ~14ms per run. ✓

---

### Task 1: Update `mesh_audit_node.py` to call real agnirt

**Files:**
- Modify: `mesh_audit_node.py`

**Step 1: Make the edit**

Replace the entire file with this implementation:

```python
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
```

**Step 2: Quick smoke-test from the terminal (no ComfyUI needed)**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
python3 -c "
import sys
sys.path.insert(0, '.')

# Stub folder_paths so we don't need ComfyUI installed
import types, tempfile
fp = types.ModuleType('folder_paths')
fp.get_temp_directory = lambda: tempfile.mkdtemp(prefix='mesh_audit_smoke_')
sys.modules['folder_paths'] = fp

from mesh_audit_node import PulseMeshAudit
n = PulseMeshAudit()
result = n.execute('/home/krishnan/dev/Assets/glTF-Sample-Assets/Models/BrainStem/glTF-Binary/BrainStem.glb')
imgs = result['ui']['images']
lbls = result['ui']['mesh_audit_carousel'][0]['labels']
print(f'Got {len(imgs)} images, {len(lbls)} labels')
for i, lbl in enumerate(lbls):
    print(f'  [{i:02d}] {lbl}  ->  {imgs[i][\"filename\"]}')
"
```

Expected output:
```
Got 16 images, 16 labels
  [00] Perspective • Path Trace  ->  ma_<id>_pathtracing_perspective.png
  [01] Perspective • Wireframe   ->  ma_<id>_wireframe_perspective.png
  ...
  [15] Left • Sliver Tri         ->  ma_<id>_sliver-triangles_left.png
```

**Step 3: Commit**

```bash
git add mesh_audit_node.py
git commit -m "feat: integrate real agnirt binary for mesh rendering"
```

---

### Task 2: Update CLAUDE.md to reflect new state

**Files:**
- Modify: `CLAUDE.md`

Remove the "prototype" and "no-op echo" language. Update:
- "Current status" section: change from placeholder to real integration
- "Prototype → Production Migration" section: mark step 1 as done (subprocess already real)
- `AGNIRT_BUILD_DIR` reference is gone; note the bundled binary path instead

---

## What's NOT changing

- `__init__.py` — untouched
- `web/js/mesh_audit_carousel.js` — untouched; carousel JS already handles real images the same way it handled placeholders
- Image matrix order and label format — unchanged

