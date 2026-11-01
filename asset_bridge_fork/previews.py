from pathlib import Path
from typing import Dict
from bpy.types import ImagePreview as P
from bpy.utils import previews
from .constants import DIRS

preview_collections: Dict[str, Dict[str, P]] = {}


def get_icon(name: str) -> P:
    return preview_collections["icons"][name].icon_id


class Icons():

    # Add icons as properties here (the preview collection is only filled at register time):
    # name: int = property(lambda _: get_icon("name"))
    pass


ICONS = Icons()


def load_icon(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Could not load file '{path}' as it doesn't exist")
    coll = preview_collections.get("icons")
    if not coll:
        coll = previews.new()
    coll.load(path.stem, str(path), "IMAGE")
    preview_collections["icons"] = coll


def register():
    if DIRS.icons.exists():
        for f in DIRS.icons.iterdir():
            load_icon(f)


def unregister():
    for coll in preview_collections.values():
        coll.close()