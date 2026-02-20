# Binary Requirements & Dependencies

This document details the system and library requirements for the bundled agnirt binary and ComfyUI-Pulse-MeshAudit plugin.

## System Requirements

### Minimum

| Component | Requirement |
|-----------|-------------|
| **OS** | Linux x64 |
| **CPU** | Any x86-64 processor (2+ cores recommended) |
| **RAM** | 2GB minimum, 8GB+ recommended |
| **Storage** | 500MB for plugin + agnirt binary |
| **GPU** | Optional; Vulkan software rendering available |

### Recommended

| Component | Recommendation |
|-----------|---|
| **CPU** | 4+ cores, modern x86-64 (2019+) |
| **RAM** | 16GB+ for batch processing |
| **GPU** | NVIDIA/AMD with Vulkan support (3x-10x speedup) |
| **Storage** | SSD for faster file I/O |

## agnirt Binary

### Build Information

- **Name:** `agnirt`
- **Location:** `bin/linux-x64/agnirt`
- **Size:** ~450MB
- **Type:** Vulkan headless renderer
- **Build Date:** See binary metadata
- **Architecture:** x86-64

### Runtime Dependencies

The agnirt binary requires the following shared libraries (included in `bin/linux-x64/`):

#### Required Libraries

| Library | Purpose | Notes |
|---------|---------|-------|
| `libcrt_vulkan.so` | Vulkan runtime | Must be on LD_LIBRARY_PATH |
| `libOpenImageDenoise.so.2` | Denoising | Optional; improves render quality |
| `libOpenImageDenoise.so.2.3.3` | Denoising (specific) | Supports OIDN 2.3.3 |
| `libOpenImageDenoise_core.so.2.3.3` | Denoising core | OIDN backend |
| `libOpenImageDenoise_device_cuda.so.2.3.3` | CUDA support | For NVIDIA GPUs |

#### Asset Files

| File | Purpose | Size |
|------|---------|------|
| `assets/sunny_rose_garden_4k.exr` | HDRI environment map | ~45MB |
| `assets/uv_checker_512.png` | UV reference texture | ~200KB |

### Vulkan Support

agnirt requires Vulkan 1.2+:

**NVIDIA GPUs:**
```bash
# Install NVIDIA Vulkan drivers
sudo apt-get install nvidia-driver-XXX nvidia-utils

# Verify
vulkaninfo | grep apiVersion
```

**AMD GPUs:**
```bash
# Install AMDGPU drivers
sudo apt-get install mesa-vulkan-drivers

# Verify
vulkaninfo | grep apiVersion
```

**Software Rendering (CPU only):**
```bash
# Install SwiftShader or LLVMpipe
sudo apt-get install libvulkan1 vulkan-tools

# Performance: ~100ms per 16-render batch (vs 14ms on GPU)
```

### Performance Metrics

#### GPU Rendering (NVIDIA RTX 3080)
- **Per batch (16 renders):** 14ms
- **Throughput:** ~57 batches/sec
- **VRAM:** ~2GB per batch (concurrent)

#### CPU Rendering (Intel Xeon, 16 cores)
- **Per batch (16 renders):** 800ms
- **Throughput:** ~1.2 batches/sec
- **RAM:** ~4GB per batch

## ComfyUI Requirements

### Plugin Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **Python** | 3.8+ | Runtime |
| **ComfyUI** | Latest | Node framework |

### Python Standard Library (no external packages required)

- `subprocess` — Execute agnirt binary
- `os` — File operations
- `json` — Parse audit_log.json
- `glob` — Find audit_log files
- `uuid` — Generate run IDs
- `time` — Caching/timing

## Operating System Specifics

### Linux (Supported)

```bash
# Ubuntu/Debian
sudo apt-get install vulkan-tools libvulkan1

# RedHat/CentOS
sudo yum install vulkan-tools vulkan-loader
```

### macOS (Not Supported)

- agnirt binary not available for macOS
- Vulkan support limited (use MoltenVK wrapper)
- Pull requests welcome for cross-platform builds

### Windows (Not Supported)

- agnirt binary not available for Windows
- Would require separate Windows build
- Pull requests welcome for Windows support

## Docker Support

For containerized deployment:

```dockerfile
FROM ubuntu:22.04

# Install Vulkan
RUN apt-get update && apt-get install -y \
    vulkan-tools \
    libvulkan1 \
    mesa-vulkan-drivers

# Copy plugin
COPY ComfyUI-Pulse-MeshAudit /comfyui/custom_nodes/ComfyUI-Pulse-MeshAudit

# Ensure agnirt is executable
RUN chmod +x /comfyui/custom_nodes/ComfyUI-Pulse-MeshAudit/bin/linux-x64/agnirt
```

## Verification Checklist

Before running the plugin:

- [ ] OS is Linux x64
- [ ] Vulkan runtime installed (`vulkan-info` works)
- [ ] agnirt binary exists and is executable: `ls -x bin/linux-x64/agnirt`
- [ ] agnirt libraries present: `ls bin/linux-x64/lib*.so`
- [ ] Asset files present: `ls bin/linux-x64/assets/`
- [ ] Python 3.8+ available: `python3 --version`
- [ ] ComfyUI is installed and running

## Troubleshooting Binary Issues

### "agnirt: command not found"

```bash
# Verify it exists
file bin/linux-x64/agnirt

# Check if it's executable
ls -l bin/linux-x64/agnirt
# Should show: -rwxr-xr-x

# Make executable
chmod +x bin/linux-x64/agnirt
```

### "libcrt_vulkan.so: cannot open shared object"

```bash
# agnirt sets LD_LIBRARY_PATH automatically, but verify:
cd bin/linux-x64
LD_LIBRARY_PATH=$(pwd) ./agnirt --version

# Or add to your shell profile:
export LD_LIBRARY_PATH=/path/to/plugin/bin/linux-x64:$LD_LIBRARY_PATH
```

### "No Vulkan drivers found"

```bash
# Check Vulkan support
vulkan-info

# Install appropriate driver (see "Vulkan Support" section above)
```

### "Not enough memory"

- Reduce concurrent renders: Lower batch size
- Increase swap: `sudo swapon -s`
- Use CPU rendering: Performance degradation but lower memory usage

## Building agnirt from Source

See [agnirt GitHub](https://github.com/pulze/agnirt) for build instructions.

Summary:
```bash
git clone https://github.com/pulze/agnirt.git
cd agnirt
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j$(nproc)
# Binary at: ./bin/agnirt
```

---

**Last Updated:** February 2026
