# Mesh Audit Stats Panel Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a collapsible "Asset Stats" accordion panel to the PulseMeshAudit node UI, displaying mesh statistics from audit_log.json alongside the 16-image carousel.

**Architecture:** 
- Backend reads `audit_log.json` from temp directory after agnirt execution
- Parses and extracts mesh stats (geometry counts, quality metrics)
- Returns structured data in node response under `asset_stats` key
- Frontend builds accordion DOM with three sections and handles expand/collapse via CSS classes

**Tech Stack:** Python (json, os modules), JavaScript (DOM manipulation), CSS (accordion styling)

---

## Task 1: Add audit_log parsing helper to mesh_audit_node.py

**Files:**
- Modify: `mesh_audit_node.py` (add new helper function before `execute()`)

**Step 1: Write the failing test**

Since we're not using a formal test framework, we'll write a standalone test script first.

Create `test_audit_log_parsing.py` in the root directory:

```python
"""Test audit_log.json parsing helper."""
import json
import tempfile
import os

def test_parse_audit_log():
    """Test that _parse_audit_log extracts correct stats from audit_log.json"""
    # Create a temporary audit_log.json
    audit_data = {
        "asset": {
            "name": "TestMesh",
            "timestamp": "2026-02-20 12:25:14"
        },
        "scene_stats": {
            "edge_count": 1000,
            "face_count": 500,
            "vertex_count": 600,
            "geometries": 1,
            "meshes": 1
        },
        "validation": {
            "degenerate_triangles": 10,
            "inverted_triangles": 50,
            "non_manifold_edges": 5,
            "sliver_triangles": {
                "count": 100,
                "percentage": 20.0,
                "threshold": 20.0
            }
        }
    }
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "audit_log.json")
        with open(log_path, 'w') as f:
            json.dump(audit_data, f)
        
        # Import after creating test data
        from mesh_audit_node import _parse_audit_log
        
        result = _parse_audit_log(log_path, 500)  # 500 = face_count for degenerate %
        
        assert result is not None
        assert result["scene"]["name"] == "TestMesh"
        assert result["scene"]["timestamp"] == "2026-02-20 12:25:14"
        assert result["geometry"]["edge_count"] == 1000
        assert result["geometry"]["face_count"] == 500
        assert result["geometry"]["vertex_count"] == 600
        assert result["quality_metrics"]["degenerate_triangles_pct"] == 2.0  # 10/500
        assert result["quality_metrics"]["sliver_triangles_pct"] == 20.0
        assert result["quality_metrics"]["inverted_triangles_pct"] == 10.0  # 50/500
        
        print("✓ All tests passed")

if __name__ == "__main__":
    test_parse_audit_log()
```

**Step 2: Run test to verify it fails**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
python3 test_audit_log_parsing.py
```

Expected output: `ModuleNotFoundError: No module named '_parse_audit_log'` or similar import error.

**Step 3: Write minimal implementation**

Add this helper function to `mesh_audit_node.py` (before the `PulseMeshAudit` class definition):

```python
import json

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
```

**Step 4: Run test to verify it passes**

```bash
python3 test_audit_log_parsing.py
```

Expected output: `✓ All tests passed`

**Step 5: Commit**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
git add mesh_audit_node.py test_audit_log_parsing.py
git commit -m "feat: add audit_log.json parsing helper function"
```

---

## Task 2: Integrate audit_log parsing into execute() method

**Files:**
- Modify: `mesh_audit_node.py` (update `execute()` method)

**Step 1: Locate the return statement in execute()**

In the `execute()` method of `PulseMeshAudit` class, find the final return statement (around line 136).

**Step 2: Update execute() to read and parse audit_log.json**

Replace the final return statement with this updated version:

```python
        # Locate and parse audit_log.json if available
        audit_log_path = os.path.join(temp_dir, "audit_log.json")
        asset_stats = None
        if os.path.isfile(audit_log_path):
            asset_stats = _parse_audit_log(audit_log_path, len(MODES) * len(CAMERAS))
        else:
            print(f"Note: audit_log.json not found at {audit_log_path}")

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
```

**Step 3: Verify the change compiles**

```bash
python3 -m py_compile mesh_audit_node.py
```

Expected: No output (success) or syntax error if something is wrong.

**Step 4: Run the smoke test to ensure existing functionality still works**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
python3 -c "
import sys, types, tempfile
sys.path.insert(0, '.')
fp = types.ModuleType('folder_paths')
temp = tempfile.mkdtemp(prefix='mesh_audit_smoke_')
fp.get_temp_directory = lambda: temp
sys.modules['folder_paths'] = fp
from mesh_audit_node import PulseMeshAudit
n = PulseMeshAudit()
result = n.execute('/home/krishnan/dev/Assets/glTF-Sample-Assets/Models/BrainStem/glTF-Binary/BrainStem.glb')
print('Result keys:', list(result['ui'].keys()))
print('Has images:', 'images' in result['ui'])
print('Has carousel:', 'mesh_audit_carousel' in result['ui'])
print('Has asset_stats:', 'asset_stats' in result['ui'])
"
```

Expected output:
```
Result keys: ['images', 'mesh_audit_carousel']
Has images: True
Has carousel: True
Has asset_stats: False
```

(asset_stats will be False because agnirt needs to write audit_log.json, which we haven't done yet)

**Step 5: Commit**

```bash
git add mesh_audit_node.py
git commit -m "feat: integrate audit_log parsing into execute() method"
```

---

## Task 3: Build accordion HTML structure in mesh_audit_carousel.js

**Files:**
- Modify: `web/js/mesh_audit_carousel.js` (add accordion building function)

**Step 1: Read the current carousel.js structure**

Review the existing `web/js/mesh_audit_carousel.js` to understand the DOM building pattern.

**Step 2: Add accordion builder function**

Add this new function to `mesh_audit_carousel.js` (before the main `onExecuted` or extension registration):

```javascript
/**
 * Build the Asset Stats accordion panel
 * @param {Object} stats - asset_stats object from node response
 * @returns {HTMLElement} - Root div containing accordion
 */
function buildAssetStatsAccordion(stats) {
    const container = document.createElement('div');
    container.className = 'asset-stats-panel';
    
    // Header (clickable to toggle)
    const header = document.createElement('div');
    header.className = 'asset-stats-header';
    header.innerHTML = '▼ Asset Stats';
    
    // Content container (will be hidden when collapsed)
    const content = document.createElement('div');
    content.className = 'asset-stats-content';
    
    // Scene Metadata section
    const sceneSection = document.createElement('div');
    sceneSection.className = 'asset-stats-section';
    sceneSection.innerHTML = `
        <div class="asset-stats-section-title">Scene Metadata</div>
        <div class="asset-stats-item">
            <span class="label">Asset Name:</span>
            <span class="value">${escapeHtml(stats.scene.name)}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Timestamp:</span>
            <span class="value">${escapeHtml(stats.scene.timestamp)}</span>
        </div>
    `;
    
    // Geometry Stats section
    const geoSection = document.createElement('div');
    geoSection.className = 'asset-stats-section';
    geoSection.innerHTML = `
        <div class="asset-stats-section-title">Geometry Stats</div>
        <div class="asset-stats-item">
            <span class="label">Edge Count:</span>
            <span class="value">${stats.geometry.edge_count.toLocaleString()}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Face Count:</span>
            <span class="value">${stats.geometry.face_count.toLocaleString()}</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Vertex Count:</span>
            <span class="value">${stats.geometry.vertex_count.toLocaleString()}</span>
        </div>
    `;
    
    // Quality Metrics section
    const qualitySection = document.createElement('div');
    qualitySection.className = 'asset-stats-section';
    qualitySection.innerHTML = `
        <div class="asset-stats-section-title">Quality Metrics</div>
        <div class="asset-stats-item">
            <span class="label">Degenerate Triangles:</span>
            <span class="value">${stats.quality_metrics.degenerate_triangles_pct.toFixed(2)}%</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Sliver Triangles:</span>
            <span class="value">${stats.quality_metrics.sliver_triangles_pct.toFixed(2)}%</span>
        </div>
        <div class="asset-stats-item">
            <span class="label">Inverted Triangles:</span>
            <span class="value">${stats.quality_metrics.inverted_triangles_pct.toFixed(2)}%</span>
        </div>
    `;
    
    // Assemble content
    content.appendChild(sceneSection);
    content.appendChild(geoSection);
    content.appendChild(qualitySection);
    
    // Assemble container
    container.appendChild(header);
    container.appendChild(content);
    
    // Add expand/collapse handler
    let expanded = true;
    header.addEventListener('click', () => {
        expanded = !expanded;
        if (expanded) {
            content.style.display = 'block';
            header.innerHTML = '▼ Asset Stats';
        } else {
            content.style.display = 'none';
            header.innerHTML = '▶ Asset Stats';
        }
    });
    
    return container;
}

/**
 * Escape HTML special characters for safe display
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
```

**Step 3: Integrate accordion into carousel widget setup**

Find the `onExecuted` handler or widget building code where the carousel is currently set up. Add this logic to display the accordion alongside the carousel:

Locate the section where the carousel DOM is created (likely in `onExecuted`). After building the carousel, add:

```javascript
    // If asset_stats are present, build and add the accordion panel
    if (nodeData.ui && nodeData.ui.asset_stats) {
        const accordion = buildAssetStatsAccordion(nodeData.ui.asset_stats);
        
        // Create a flex container for carousel + accordion
        const mainContainer = document.createElement('div');
        mainContainer.style.display = 'flex';
        mainContainer.style.gap = '20px';
        
        // Move existing carousel into left side
        const carouselContainer = document.createElement('div');
        carouselContainer.style.flex = '1';
        carouselContainer.appendChild(carouselElement); // existing carousel
        
        // Add accordion on right side
        const statsContainer = document.createElement('div');
        statsContainer.style.flex = '0 0 300px';
        statsContainer.appendChild(accordion);
        
        // Assemble main container
        mainContainer.appendChild(carouselContainer);
        mainContainer.appendChild(statsContainer);
        
        // Add to widget (replace existing carousel element reference)
        // This depends on your current carousel setup
    }
```

**Step 4: Verify JavaScript syntax**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
node -c web/js/mesh_audit_carousel.js
```

Expected: No output (success).

**Step 5: Commit**

```bash
git add web/js/mesh_audit_carousel.js
git commit -m "feat: add accordion DOM builder and integration logic"
```

---

## Task 4: Add CSS styling for accordion

**Files:**
- Create: `web/css/mesh_audit_carousel.css` (or add to existing if present)

**Step 1: Create/update stylesheet**

Check if `web/css/mesh_audit_carousel.css` exists. If not, create it:

```css
/* Asset Stats Accordion Styling */

.asset-stats-panel {
    display: flex;
    flex-direction: column;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: #f9f9f9;
}

.asset-stats-header {
    padding: 12px;
    background-color: #e8e8e8;
    cursor: pointer;
    font-weight: 600;
    font-size: 14px;
    border-bottom: 1px solid #ddd;
    user-select: none;
    transition: background-color 0.2s;
}

.asset-stats-header:hover {
    background-color: #d8d8d8;
}

.asset-stats-content {
    display: block;
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.asset-stats-content.collapsed {
    display: none;
}

.asset-stats-section {
    padding: 12px;
    border-bottom: 1px solid #eee;
}

.asset-stats-section:last-child {
    border-bottom: none;
}

.asset-stats-section-title {
    font-weight: 600;
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
}

.asset-stats-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 13px;
}

.asset-stats-item:last-child {
    margin-bottom: 0;
}

.asset-stats-item .label {
    font-weight: 500;
    color: #666;
}

.asset-stats-item .value {
    color: #333;
    font-family: monospace;
    text-align: right;
}

/* Responsive adjustments */
@media (max-width: 1200px) {
    .asset-stats-panel {
        flex: 1;
        min-width: 250px;
    }
}
```

**Step 2: Link stylesheet in web page**

If `web/index.html` or the ComfyUI extension entry point exists, ensure the CSS is loaded. Add or update the link:

```html
<link rel="stylesheet" href="css/mesh_audit_carousel.css">
```

Or if using a JavaScript-based extension registration, inline the styles in the JS file or add via `document.head`.

**Step 3: Verify CSS has no syntax errors**

Manual review of the CSS above confirms it's valid.

**Step 4: Commit**

```bash
git add web/css/mesh_audit_carousel.css
git commit -m "style: add accordion styling for asset stats panel"
```

---

## Task 5: Update JavaScript toggle logic to use CSS class

**Files:**
- Modify: `web/js/mesh_audit_carousel.js` (update accordion handler)

**Step 1: Refine the toggle logic**

Update the event listener in the `buildAssetStatsAccordion` function to use CSS classes instead of inline styles:

Replace the event listener code with:

```javascript
    // Add expand/collapse handler
    let expanded = true;
    header.addEventListener('click', () => {
        expanded = !expanded;
        if (expanded) {
            content.classList.remove('collapsed');
            header.innerHTML = '▼ Asset Stats';
        } else {
            content.classList.add('collapsed');
            header.innerHTML = '▶ Asset Stats';
        }
    });
```

And update the CSS in `web/css/mesh_audit_carousel.css` to handle the collapsed class:

```css
.asset-stats-content.collapsed {
    max-height: 0;
    overflow: hidden;
    padding: 0;
    border: none;
}
```

**Step 2: Commit**

```bash
git add web/js/mesh_audit_carousel.js web/css/mesh_audit_carousel.css
git commit -m "refactor: improve accordion toggle with CSS classes"
```

---

## Task 6: Integration test with real agnirt output

**Files:**
- Create: `test_full_integration.py` (temporary test script)

**Step 1: Run agnirt and capture audit_log.json**

First, ensure agnirt writes audit_log.json. You mentioned fixing this — for now, create a mock audit_log.json for testing:

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit

# Create temp directory with test audit_log.json
mkdir -p /tmp/test_audit
cat > /tmp/test_audit/audit_log.json << 'EOF'
{
    "asset": {
        "name": "TestMesh",
        "timestamp": "2026-02-20 15:30:45"
    },
    "scene_stats": {
        "edge_count": 15000,
        "face_count": 8000,
        "vertex_count": 9500,
        "geometries": 1,
        "instances": 1,
        "materials": 2,
        "meshes": 1,
        "parameterized_meshes": 1,
        "textures": 4
    },
    "validation": {
        "degenerate_triangles": 12,
        "inverted_triangles": 240,
        "non_manifold_edges": 100,
        "sliver_triangles": {
            "count": 320,
            "percentage": 4.0,
            "threshold": 20.0
        }
    },
    "status": "FAIL"
}
EOF
```

**Step 2: Create integration test**

```python
"""Integration test for audit_log parsing with real structure"""
import json
import tempfile
import os

def test_integration():
    """Test full integration of audit_log parsing and UI response structure"""
    import sys, types
    
    # Stub folder_paths
    fp = types.ModuleType('folder_paths')
    temp = tempfile.mkdtemp(prefix='mesh_audit_test_')
    fp.get_temp_directory = lambda: temp
    sys.modules['folder_paths'] = fp
    
    # Copy audit_log.json to temp directory
    test_audit_path = "/tmp/test_audit/audit_log.json"
    temp_audit_path = os.path.join(temp, "audit_log.json")
    
    if os.path.exists(test_audit_path):
        with open(test_audit_path, 'r') as src:
            data = json.load(src)
        with open(temp_audit_path, 'w') as dst:
            json.dump(data, dst)
    
    from mesh_audit_node import PulseMeshAudit
    n = PulseMeshAudit()
    
    # Note: This will fail if agnirt isn't available or mesh file missing
    # For now, just test the parsing function directly
    from mesh_audit_node import _parse_audit_log
    
    result = _parse_audit_log(temp_audit_path, 8000)
    
    assert result is not None, "Parsing returned None"
    assert result["scene"]["name"] == "TestMesh"
    assert result["geometry"]["edge_count"] == 15000
    assert result["quality_metrics"]["sliver_triangles_pct"] == 4.0
    assert result["quality_metrics"]["degenerate_triangles_pct"] == 0.15  # 12/8000
    assert result["quality_metrics"]["inverted_triangles_pct"] == 3.0  # 240/8000
    
    print("✓ Integration test passed")
    print(f"  - Scene: {result['scene']['name']}")
    print(f"  - Geometry: {result['geometry']['edge_count']} edges, {result['geometry']['face_count']} faces")
    print(f"  - Quality: {result['quality_metrics']['degenerate_triangles_pct']}% degenerate")

if __name__ == "__main__":
    test_integration()
```

**Step 3: Run test**

```bash
python3 test_full_integration.py
```

Expected output:
```
✓ Integration test passed
  - Scene: TestMesh
  - Geometry: 15000 edges, 8000 faces
  - Quality: 0.15% degenerate
```

**Step 4: Clean up test files**

```bash
rm test_audit_log_parsing.py test_full_integration.py
git add -A
```

---

## Task 7: Verify no regression in carousel functionality

**Files:**
- No changes (verification only)

**Step 1: Run existing smoke test**

```bash
cd /home/krishnan/dev/ComfyUI-Pulse-MeshAudit
python3 -c "
import sys, types, tempfile
sys.path.insert(0, '.')
fp = types.ModuleType('folder_paths')
temp = tempfile.mkdtemp(prefix='mesh_audit_verify_')
fp.get_temp_directory = lambda: temp
sys.modules['folder_paths'] = fp
from mesh_audit_node import PulseMeshAudit
n = PulseMeshAudit()
result = n.execute('/home/krishnan/dev/Assets/glTF-Sample-Assets/Models/BrainStem/glTF-Binary/BrainStem.glb')
print(f'Images: {len(result[\"ui\"][\"images\"])}')
print(f'Labels: {len(result[\"ui\"][\"mesh_audit_carousel\"][0][\"labels\"])}')
print(f'Asset stats present: {\"asset_stats\" in result[\"ui\"]}')
assert len(result['ui']['images']) == 16
assert len(result['ui']['mesh_audit_carousel'][0]['labels']) == 16
print('✓ Carousel functionality intact')
"
```

Expected output:
```
Images: 16
Labels: 16
Asset stats present: False
✓ Carousel functionality intact
```

**Step 2: Verify in ComfyUI UI (manual)**

Once integrated into ComfyUI:
1. Add the PulseMeshAudit node
2. Load a mesh file
3. Execute
4. Verify 16-image carousel renders
5. Verify "Asset Stats" header appears to the right
6. Click header to expand/collapse
7. Verify all stats display correctly

**Step 3: Final commit**

```bash
git status  # Should be clean
git log --oneline | head -10  # Review recent commits
```

---

## Summary

**7 tasks, estimated 30-45 minutes total:**

1. ✓ Add audit_log parsing helper (5 min)
2. ✓ Integrate into execute() (5 min)
3. ✓ Build accordion HTML structure (10 min)
4. ✓ Add CSS styling (5 min)
5. ✓ Refine toggle logic (5 min)
6. ✓ Integration testing (5 min)
7. ✓ Verify no regression (5 min)

**Key files modified:**
- `mesh_audit_node.py` (backend parsing + integration)
- `web/js/mesh_audit_carousel.js` (accordion DOM + JS logic)
- `web/css/mesh_audit_carousel.css` (new file, accordion styles)

**Commits to expect:**
1. feat: add audit_log.json parsing helper function
2. feat: integrate audit_log parsing into execute() method
3. feat: add accordion DOM builder and integration logic
4. style: add accordion styling for asset stats panel
5. refactor: improve accordion toggle with CSS classes

---

## Plan complete! 

Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review code between tasks, fast iteration

**2. Parallel Session (separate)** — Open new session with `superpowers:executing-plans`, batch execution with checkpoints

Which approach would you prefer?
