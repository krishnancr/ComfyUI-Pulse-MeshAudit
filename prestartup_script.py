import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
COMFYUI_DIR = SCRIPT_DIR.parent.parent

dest = COMFYUI_DIR / "input" / "3d"
dest.mkdir(parents=True, exist_ok=True)

print(f"[MeshAudit] Copying assets from {SCRIPT_DIR / 'assets'} to {dest}")

for src in (SCRIPT_DIR / "assets").glob("**/*"):
    if src.is_file():
        print(f"[MeshAudit] Copying {src.name} ...")
        shutil.copy2(src, dest / src.name)
        print(f"[MeshAudit] Done: {src.name}")

print("[MeshAudit] Asset copy complete.")
