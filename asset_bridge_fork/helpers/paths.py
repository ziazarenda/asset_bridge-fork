# SPDX-License-Identifier: GPL-3.0-or-later
"""Open local files and folders through Blender's operating-system integration."""

from pathlib import Path
import bpy


def open_local_path(path):
    path = Path(bpy.path.abspath(str(path))).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    result = bpy.ops.wm.path_open(filepath=str(path))
    if "FINISHED" not in result:
        raise OSError(f"Could not open {path} with its default application")
