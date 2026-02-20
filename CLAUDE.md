# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A ComfyUI custom node plugin (`ComfyUI-Pulse-MeshAudit`) that audits 3D mesh files by running the `agnirt` headless renderer and displaying a carousel of output renders inside the node UI.

**Current status:** Real agnirt integration complete. All 16 renders produced by the bundled `bin/linux-x64/agnirt` binary on each execute call; no placeholder images.

## Architecture

```
mesh_audit_node.py (PulseMeshAudit)
  ├── INPUT: file_path (STRING) — path to .glb/.obj/.gltf
  ├── subprocess.run([bin/linux-x64/agnirt, "vulkan", file_path,
  │     "-headless", "-shading-mode", "all",
  │     "--camera", "perspective", "front", "right", "left",
  │     "-o", "<comfyui_temp>/ma_<run_id>.png"])
  ├── agnirt writes 16 PNGs: ma_<run_id>_<mode>_<camera>.png
  └── Return {"ui": {"images": [...], "mesh_audit_carousel": [{"labels": [...]}]}}

web/js/mesh_audit_carousel.js (Pulse.MeshAuditCarousel extension)
  ├── Hooks onExecuted on PulseMeshAudit nodes
  ├── Suppresses ComfyUI default image preview (overrides this.imgs getter/setter)
  ├── Builds carousel DOM: <img> + ◄ label ► navigation
  └── Images fetched via /view?filename=...&type=temp
```

**Node properties:** `RETURN_TYPES = ()`, `OUTPUT_NODE = True`, `IS_CHANGED` returns `time.time()` (always re-executes).

**16 image matrix:** Cameras × Modes = `["Perspective","Front","Right","Left"]` × `["Path Trace","Wireframe","Geo Analysis","Sliver Tri"]`. Labels formatted as `"{camera} • {mode}"`.

## Development Setup

Install into ComfyUI by symlinking or copying this directory into `ComfyUI/custom_nodes/`. Then restart ComfyUI.

```bash
# Run ComfyUI (from ComfyUI root)
python3 main.py

# Test the Python node in isolation (once mesh_audit_node.py exists)
python3 -c "from mesh_audit_node import PulseMeshAudit; n = PulseMeshAudit(); print(n.execute('/tmp/test.glb'))"
```

## Smoke Test (no ComfyUI needed)

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
python3 -c "
import sys, types, tempfile
sys.path.insert(0, '.')
fp = types.ModuleType('folder_paths')
fp.get_temp_directory = lambda: tempfile.mkdtemp(prefix='mesh_audit_smoke_')
sys.modules['folder_paths'] = fp
from mesh_audit_node import PulseMeshAudit
n = PulseMeshAudit()
result = n.execute('/home/krishnan/dev/Assets/glTF-Sample-Assets/Models/BrainStem/glTF-Binary/BrainStem.glb')
imgs = result['ui']['images']
lbls = result['ui']['mesh_audit_carousel'][0]['labels']
print(f'Got {len(imgs)} images, {len(lbls)} labels')
"
```

Expected: `Got 16 images, 16 labels`

## Reference Implementations

The design references two existing nodes in other repos on this machine:
- `AgniRT/agnirt_node/agnirt_node.py` — subprocess + `ui.images` pattern, `IS_CHANGED`, daemon lifecycle
- `AgniRT/agnirt_node/web/js/agnirt_viewer.js` — `addDOMWidget`, `onExecuted`, `imgs` suppression pattern
