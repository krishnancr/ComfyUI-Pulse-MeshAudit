# Contributing to ComfyUI-Pulse-MeshAudit

Thank you for your interest in contributing! This document provides guidelines for participating in the project.

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Focus on the code, not the person
- Help others learn and grow

## How to Contribute

### Reporting Bugs

**Before submitting:** Check existing [issues](https://github.com/yourusername/ComfyUI-Pulse-MeshAudit/issues) to avoid duplicates.

**When submitting:**
1. Use a clear, descriptive title
2. Describe the exact steps to reproduce
3. Provide actual vs. expected behavior
4. Include screenshots/logs if relevant
5. List your environment:
   - OS and version
   - ComfyUI version
   - Python version
   - GPU/CPU model

### Suggesting Enhancements

- Explain the use case and expected behavior
- Provide examples of how it would work
- Explain why this enhancement would be useful
- Consider alternative approaches

### Pull Requests

1. **Fork** the repository
2. **Create a branch:** `git checkout -b feature/descriptive-name`
3. **Make changes** following code style (see below)
4. **Test** your changes thoroughly
5. **Commit** with clear, atomic commits
6. **Push** to your fork
7. **Open a PR** with:
   - Clear title and description
   - Reference to related issues
   - Screenshots/demos for UI changes
   - Testing instructions

## Code Style

### Python

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use 4 spaces for indentation
- Max line length: 100 characters
- Use type hints for function arguments
- Add docstrings for classes and public functions

Example:
```python
def _parse_audit_log(log_path: str, total_faces: int) -> dict | None:
    """
    Parse audit_log.json and extract mesh statistics.

    Args:
        log_path: Path to audit_log.json file
        total_faces: Total face count for percentage calculations

    Returns:
        Dict with scene/geometry/quality_metrics, or None on error
    """
```

### JavaScript

- Use 2 spaces for indentation
- Use `const`/`let` (not `var`)
- Use camelCase for variables and functions
- Add comments for complex logic
- Use `console.log` with `[MeshAudit]` prefix for debugging

Example:
```javascript
function buildAssetStatsAccordion(stats) {
    // Create container
    const container = document.createElement('div');
    container.className = 'asset-stats-panel';

    // Build content...

    return container;
}
```

### CSS

- Use kebab-case for class names
- Group related properties
- Comment section headers
- Use consistent spacing and indentation

Example:
```css
.asset-stats-panel {
    display: flex;
    flex-direction: column;
    background-color: #1a1a1a;
    border: 1px solid #333;
}
```

## Commit Messages

Follow conventional commits:

```
type(scope): brief description

Optional longer explanation...

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`

Examples:
- `feat: add keyboard navigation to image viewer`
- `fix: handle missing audit_log gracefully`
- `docs: update binary requirements`

## Testing

### Python

```bash
# Test audit_log parsing
python3 -c "
import sys, types
sys.path.insert(0, '.')
fp = types.ModuleType('folder_paths')
sys.modules['folder_paths'] = fp
from mesh_audit_node import _parse_audit_log
# Test...
"
```

### JavaScript

- Test in browser console (F12)
- Check for console errors
- Test responsive layout at different widths
- Test keyboard controls: arrow keys, ESC, etc.

### Manual Testing

1. Verify node appears in ComfyUI UI
2. Load a mesh file and execute
3. Check carousel renders properly
4. Click image for fullscreen viewer
5. Test keyboard navigation
6. Expand/collapse accordion
7. Resize node and verify layout

## Documentation

- Update README.md for user-facing changes
- Update BINARY_REQUIREMENTS.md for dependency changes
- Add docstrings for new functions
- Include examples where helpful
- Keep docs in sync with code

## Areas for Contribution

### Wanted

- **Windows/macOS support** — Compile agnirt for other platforms
- **Performance optimization** — Faster parsing, better rendering
- **Additional statistics** — More mesh metrics in accordion
- **Testing** — Unit tests, integration tests
- **Documentation** — More examples, troubleshooting guides
- **UI/UX improvements** — Better carousel layout, accessibility

### Not Planned

- Non-Vulkan renderers (require agnirt rewrite)
- Real-time mesh editing (out of scope)
- Network rendering (complex architecture)

## Releases

Releases follow semantic versioning: `MAJOR.MINOR.PATCH`

- `MAJOR` — Breaking changes
- `MINOR` — New features (backward compatible)
- `PATCH` — Bug fixes

Maintainers handle releases and tagging.

## Questions?

- Check [existing issues](https://github.com/yourusername/ComfyUI-Pulse-MeshAudit/issues)
- Ask in a new issue with the `question` label
- Reference relevant documentation

---

**Thank you for contributing! 🙏**
