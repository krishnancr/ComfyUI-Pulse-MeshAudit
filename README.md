# ComfyUI Pulse MeshAudit

A ComfyUI custom node for auditing 3D mesh files by rendering them with a headless renderer and displaying an interactive carousel of renders with detailed mesh statistics.

## Features

✨ **16-Render Carousel**
- 4 camera angles (Perspective, Front, Right, Left)
- 4 shading modes (Path Trace, Wireframe, Geometry Analysis, Sliver Triangles)
- Auto-resizing grid layout with intuitive modal viewer

🖼️ **Interactive Image Viewer**
- Click any render to view fullscreen in centered modal
- Navigate with **← →** arrow keys to explore different views
- **ESC** key or **✕** button to close
- Image counter and label display

📊 **Asset Statistics Panel**
- Collapsible accordion with three categories:
  - **Scene Metadata**: Asset name, timestamp
  - **Geometry Stats**: Edge count, face count, vertex count
  - **Quality Metrics**: Degenerate/sliver/inverted triangle percentages
- Dark-themed UI matching carousel design
- Responsive layout that adapts to node size

🔍 **Real agnirt Integration**
- Uses bundled agnirt headless renderer binary
- Generates 16 PNG renders per execution (~14ms)
- Automatic audit_log.json parsing for stats

## Installation

### Requirements

- **ComfyUI** (latest)
- **Linux x64** system (Windows/macOS support via agnirt binary availability)
- **Python 3.8+**
- **~500MB** disk space for agnirt binary and assets

### Steps

1. **Clone into ComfyUI custom_nodes:**
```bash
cd /path/to/ComfyUI/custom_nodes
git clone https://github.com/yourusername/ComfyUI-Pulse-MeshAudit.git
cd ComfyUI-Pulse-MeshAudit
```

2. **Verify agnirt binary:**
```bash
ls -lh bin/linux-x64/agnirt
# Should show executable with ~450MB size
```

3. **Restart ComfyUI:**
```bash
# From ComfyUI root
python3 main.py
```

4. **Verify installation:**
   - In ComfyUI UI, search for "PulseMeshAudit" node
   - Node should appear in Pulse/MeshAudit category

## Usage

### Basic Workflow

1. **Add PulseMeshAudit node** to canvas
2. **Set file_path** to your mesh file:
   - Supported: `.glb`, `.obj`, `.gltf`
3. **Execute node** (Ctrl+Enter or click execute button)
4. **View renders**:
   - Hover over images for outline highlight
   - Click any image to view fullscreen
   - Use arrow keys to navigate between views
5. **Inspect stats**:
   - Click "Asset Stats" header to expand/collapse
   - View scene metadata, geometry counts, quality metrics

### Example Mesh Files

Test with [glTF Sample Assets](https://github.com/KhronosGroup/glTF-Sample-Assets):
```bash
# Download sample
wget https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/BrainStem/glTF-Binary/BrainStem.glb

# Use full path in node: /path/to/BrainStem.glb
```

## Technical Details

### Architecture

```
mesh_audit_node.py (Python Backend)
├── Parse file_path input
├── Execute: bin/linux-x64/agnirt vulkan <file>
│   └── Outputs 16 PNG renders + audit_log.json
├── Parse audit_log.json for mesh stats
└── Return UI response with images + stats

web/js/mesh_audit_carousel.js (JavaScript Frontend)
├── Register ComfyUI extension
├── Build 16-image carousel grid
├── Add image click → fullscreen viewer
├── Add keyboard navigation (←/→/ESC)
└── Build/display Asset Stats accordion
```

### Node Properties

| Property | Type | Description |
|----------|------|-------------|
| `file_path` | STRING | Path to mesh file (.glb/.obj/.gltf/.fbx) |
| Return Type | () | Output node (no connections) |
| `IS_CHANGED` | Time-based | Always re-executes on run |

### agnirt Command

```bash
agnirt vulkan <file_path> \
  -headless \
  -shading-mode all \
  --camera perspective front right left \
  -o <temp_dir>/ma_<run_id>.png
```

This generates 16 files:
- `ma_<run_id>_pathtracing_perspective.png`
- `ma_<run_id>_wireframe_front.png`
- ... (12 more)
- `ma_<run_id>_sliver-triangles_left.png`

### Audit Log Format

agnirt writes `audit_log_<asset>_<timestamp>.json`:

```json
{
  "asset": {
    "name": "BrainStem",
    "timestamp": "2026-02-20 16:21:30"
  },
  "scene_stats": {
    "edge_count": 39875,
    "face_count": 20066,
    "vertex_count": 21178,
    ...
  },
  "validation": {
    "degenerate_triangles": 10,
    "inverted_triangles": 50,
    "sliver_triangles": {
      "count": 100,
      "percentage": 8.34
    }
  },
  "status": "PASS"
}
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m "feat: describe your change"`
4. Push to branch: `git push origin feature/your-feature`
5. Open a Pull Request

## License

**MIT License with Commons Clause**

Free for non-commercial use. Commercial use requires explicit written permission.

See [LICENSE](LICENSE) file for full details.


