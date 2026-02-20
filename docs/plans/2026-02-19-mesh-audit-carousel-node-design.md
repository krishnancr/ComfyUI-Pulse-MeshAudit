# Mesh Audit Carousel Node — Design

**Date:** 2026-02-19
**Status:** Approved

## Goal

Build a ComfyUI custom node (`PulseMeshAudit`) that:
1. Accepts a mesh file path (GLB/OBJ/GLTF) as input
2. Runs a subprocess command (placeholder `echo`; eventually `agnirt --headless`)
3. Displays a carousel of output images directly inside the node UI

This document covers the **prototype phase**: the subprocess is a no-op `echo` command and images are Pillow-generated solid-color placeholders. The architecture is designed so that swapping in real `agnirt` output later is a one-line change.

---

## Architecture

```
User clicks "Queue Prompt"
        │
        ▼
PulseMeshAudit node (Python)
  ├── subprocess.run(["echo", file_path])    ← placeholder for agnirt
  ├── Pillow: generate 16 solid-color PNGs   ← placeholder images
  │     (4 cameras × 4 shading modes)
  ├── Save PNGs to ComfyUI temp dir
  └── Return {
        "ui": {
          "images": [{filename, subfolder, type}, ...x16],
          "mesh_audit_carousel": [{"labels": [...16 label strings...]}]
        }
      }
        │
        ▼
ComfyUI WebSocket sends ui payload to browser
        │
        ▼
mesh_audit_carousel.js extension
  ├── Intercepts onExecuted on PulseMeshAudit node
  ├── Suppresses default ComfyUI image preview widget
  ├── Builds carousel DOM: [image] + [◄ label ►]
  └── Images fetched lazily via /view?filename=...&type=temp
```

---

## Python Node

**File:** `mesh_audit_node.py`

| Property | Value |
|---|---|
| Class | `PulseMeshAudit` |
| Category | `Pulse/MeshAudit` |
| OUTPUT_NODE | `True` |
| RETURN_TYPES | `()` |
| FUNCTION | `execute` |

### Inputs

| Name | Type | Notes |
|---|---|---|
| `file_path` | STRING | Path to `.glb`, `.obj`, or `.gltf` file |

### Hardcoded constants

| Name | Value |
|---|---|
| SPP | 8 |
| Width | 1920 |
| Height | 1080 |

### Execute logic

1. `subprocess.run(["echo", f"[MeshAudit] Processing: {file_path}"])`
2. Build label matrix:
   - Cameras: `["Perspective", "Front", "Right", "Left"]`
   - Modes: `["Path Trace", "Wireframe", "Geo Analysis", "Sliver Tri"]`
   - 16 combinations: `"{camera} • {mode}"`
3. Generate one PNG per label using Pillow:
   - Size: 1920×1080
   - Each: distinct solid background color + white label text centered
   - Filename: `mesh_audit_{cam}_{mode}_{suffix}.png` (saved to ComfyUI temp dir)
4. Return:
```python
{"ui": {
    "images": [{"filename": ..., "subfolder": "", "type": "temp"}, ...],
    "mesh_audit_carousel": [{"labels": ["Perspective • Path Trace", ...]}]
}}
```

`IS_CHANGED` returns `time.time()` so re-queuing always re-executes.

---

## JS Extension

**File:** `web/js/mesh_audit_carousel.js`

Registered as `"Pulse.MeshAuditCarousel"` via `app.registerExtension`.

### onExecuted hook

1. Read `msg.mesh_audit_carousel[0].labels` (string[]) and `msg.images` ([{filename, type}])
2. Suppress ComfyUI's default preview widget:
   ```js
   Object.defineProperty(this, "imgs", { get: ()=>[], set: ()=>{}, configurable: true })
   ```
3. Tear down any existing carousel DOM widget on the node
4. Build carousel DOM:
   ```
   ┌──────────────────────────────┐
   │   <img> (100% width)         │
   ├──────────────────────────────┤
   │  ◄   Perspective • Path Trace  ►  │
   └──────────────────────────────┘
   ```
   - `img.src` = `/view?filename=...&subfolder=&type=temp`
   - ◄/► buttons increment/decrement `currentIndex` (wraps around), update `img.src` and label text
   - Images loaded lazily on navigation — only current image is fetched
5. Attach via `node.addDOMWidget("mesh_audit_carousel", "div", container, { serialize: false })`

### onRemoved hook

Remove carousel widget and clean up DOM if present.

---

## File Structure

```
ComfyUI-Pulse-MeshAudit/
├── bin/
│   └── linux-x64/
│       └── agnirt                          (existing — unused in prototype)
├── docs/
│   └── plans/
│       └── 2026-02-19-mesh-audit-carousel-node-design.md
├── __init__.py                             (NEW)
├── mesh_audit_node.py                      (NEW)
└── web/
    └── js/
        └── mesh_audit_carousel.js          (NEW)
```

---

## Prototype → Production Migration

When ready to integrate real `agnirt`:

1. Replace `subprocess.run(["echo", ...])` with `subprocess.run([AGNIRT_PATH, "--headless", "--camera", "all", "-shading-mode", "all", ...])`
2. Replace Pillow image generation with reading the PNG files agnirt writes to disk
3. No changes needed to JS extension or `__init__.py`

---

## References

- `AgniRT/agnirt_node/agnirt_node.py` — subprocess + `ui.images` pattern, `IS_CHANGED`, daemon lifecycle
- `AgniRT/agnirt_node/web/js/agnirt_viewer.js` — `addDOMWidget`, `onExecuted` intercept, `imgs` suppression pattern
- `Pulse/frontends/comfyui/Pulse-MeshValidator/mesh_validator.py` — simpler node structure reference
