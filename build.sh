#!/usr/bin/env bash
# Build the vibe5d Blender addon ZIP.
# Requirements: Python 3 (any version that ships with Blender 4.x)
#
# Usage:
#   chmod +x build.sh
#   ./build.sh
#
# Output: build/vibe5d-blender-<version>.zip

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer the Python that ships with Blender if available, else fall back to system Python 3
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python 3 not found. Install Python 3 or add Blender's Python to PATH." >&2
    exit 1
fi

echo "Using: $($PYTHON --version)"
$PYTHON build.py
