#!/usr/bin/env python3
"""
Build script: creates a Blender-installable ZIP of the vibe4d addon.

Usage:
    python build.py          # from the repo root
    ./build.sh               # Unix/macOS wrapper
    build.bat                # Windows wrapper

Output: build/vibe4d-blender-{version}.zip

Install in Blender:
    Edit > Preferences > Add-ons > Install... > select the .zip
"""
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent
ADDON_NAME = "vibe4d"

# Directories and files to exclude from the ZIP
EXCLUDE_DIRS = {".git", "__pycache__", "docs", "build", ".vscode", ".idea"}
EXCLUDE_NAMES = {
    ".gitignore", ".gitattributes",
    "build.py", "build.sh", "build.bat",
}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
# Sub-paths (using forward slashes) to exclude
EXCLUDE_PATH_PREFIXES = (
    "packages/websocket/tests",
)


def get_version() -> str:
    text = (ROOT / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', text)
    return f"{m.group(1)}.{m.group(2)}.{m.group(3)}" if m else "0.0.0"


def is_excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    rel_fwd = str(rel).replace("\\", "/")

    for part in rel.parts:
        if part in EXCLUDE_DIRS:
            return True

    for prefix in EXCLUDE_PATH_PREFIXES:
        if rel_fwd.startswith(prefix):
            return True

    if rel.name in EXCLUDE_NAMES:
        return True

    if rel.suffix in EXCLUDE_SUFFIXES:
        return True

    return False


def main() -> None:
    version = get_version()
    build_dir = ROOT / "build"
    zip_path = build_dir / f"{ADDON_NAME}-blender-{version}.zip"

    print(f"Building {ADDON_NAME} v{version} ...")
    build_dir.mkdir(exist_ok=True)

    if zip_path.exists():
        zip_path.unlink()

    added = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for src in sorted(ROOT.rglob("*")):
            if src.is_file() and not is_excluded(src):
                arc = Path(ADDON_NAME) / src.relative_to(ROOT)
                zf.write(src, arc)
                added += 1

    print(f"  {added} files packaged")
    print(f"\nRelease:  {zip_path.relative_to(ROOT)}")
    print(f"Install:  Blender → Edit → Preferences → Add-ons → Install… → {zip_path.name}")


if __name__ == "__main__":
    main()
