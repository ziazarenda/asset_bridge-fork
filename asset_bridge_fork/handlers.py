import traceback
import bpy
from bpy.app import handlers
from bpy.types import Scene

from .constants import ASSET_LIB_NAME, DIRS
from .helpers.main_thread import run_in_main_thread
from .settings import get_ab_settings


def get_asset_quality(context):
    return get_ab_settings(context).asset_quality


def get_browser_area(name) -> bpy.types.Area:
    """Find the area that has the correct asset selected in the asset browser.
    If not found returns None. This isn't perfect as if you have to asset browsers selecting the same asset,
    it will just select the first one"""
    overrides = []
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "FILE_BROWSER" and area.ui_type == "ASSETS":
                overrides.append({"window": window, "area": area})
    for override in overrides:
        with bpy.context.temp_override(**override):
            handle = bpy.context.asset
            if handle and handle.metadata.description == name:
                return override["area"]
    else:
        if overrides:
            return overrides[0]["area"]
    return None


def link_method(area):
    if area is None:
        return "APPEND_REUSE"
    import_method = area.spaces.active.params.import_method
    if import_method == "FOLLOW_PREFS":
        lib = bpy.context.preferences.filepaths.asset_libraries.get(ASSET_LIB_NAME)
        import_method = lib.import_method if lib else "APPEND_REUSE"
    # PACK is newer than this add-on's import backend. Import independent data;
    # texture packing remains controlled by Asset Bridge's Auto pack files.
    if import_method == "PACK":
        return "APPEND"
    return import_method


prev_materials = {}
prev_world = {}


_pending_scene_names = set()
_processing_imports = False


def _process_pending_imports():
    """Run imports outside dependency-graph evaluation, where context overrides work."""
    global _processing_imports
    manager = getattr(bpy.context, "window_manager", None)
    if manager is not None and manager.is_interface_locked:
        return 0.1
    names = tuple(_pending_scene_names)
    _pending_scene_names.clear()
    _processing_imports = True
    try:
        for name in names:
            scene = bpy.data.scenes.get(name)
            if scene is not None:
                try:
                    with bpy.context.temp_override(scene=scene):
                        _process_scene_imports(scene, None)
                except Exception:
                    traceback.print_exc()
    finally:
        _processing_imports = False
    return None


@handlers.persistent
def depsgraph_update_pre_handler(scene: Scene, _):
    """Coalesce graph notifications; never import or override context here."""
    if bpy.app.background or _processing_imports:
        return
    _pending_scene_names.add(scene.name)
    if not bpy.app.timers.is_registered(_process_pending_imports):
        bpy.app.timers.register(_process_pending_imports, first_interval=0.01)


def _process_scene_imports(scene: Scene, _):
    """Check if an asset has been dragged from the asset browser"""

    if bpy.app.background or not hasattr(DIRS, "assets"):
        return

    quality = get_asset_quality(bpy.context)
    reload = bpy.context.window_manager.asset_bridge.reload_asset

    # Hdris
    global prev_world
    if (world := scene.world) and world.asset_bridge.is_dummy:
        name = world.asset_bridge.idname
        bpy.data.worlds.remove(world)
        bpy.ops.asset_bridge.import_asset(
            "INVOKE_DEFAULT",
            asset_name=name,
            asset_quality=quality,
            link_method=link_method(get_browser_area(name)),
            reload=reload,
            at_mouse=True,
        )
        scene.world = prev_world.get(scene.name)

    if scene.world is not None:
        prev_world[scene.name] = scene.world

    # Materials
    global prev_materials
    for obj in scene.objects:
        for i, slot in enumerate(obj.material_slots):
            if (mat := slot.material) and mat.asset_bridge.is_dummy:
                name = mat.asset_bridge.idname
                bpy.data.materials.remove(mat)
                bpy.ops.asset_bridge.import_asset(
                    "INVOKE_DEFAULT",
                    asset_name=name,
                    at_mouse=True,
                    # location=bpy.context.object.location,
                    asset_quality=quality,
                    link_method=link_method(get_browser_area(name)),
                    reload=reload,
                    material_target=obj.name,
                    material_slot_index=i,
                )
                try:
                    slot.material = prev_materials[obj.name][i]
                except (IndexError, KeyError):
                    continue
                except ReferenceError:
                    continue

    for obj in bpy.data.objects:
        mats = [slot.material for slot in obj.material_slots]
        for i, mat in enumerate(mats):
            prev_mats = prev_materials.get(obj.name)
            if not prev_mats or len(prev_mats) != len(mats):
                continue

            if not mat:
                mats[i] = prev_mats[i]

        prev_materials[obj.name] = mats

    # Models
    objs = [o for o in scene.objects if o.asset_bridge.is_dummy]
    for obj in objs:
        name = obj.asset_bridge.idname
        obj.asset_bridge.is_dummy = False

        # For some reason in 4.1 this creates a popup for the user saying "Object not found",
        # Unless it is run in the next cycle with a timer.
        run_in_main_thread(bpy.data.objects.remove, [obj])
        bpy.ops.asset_bridge.import_asset(
            "INVOKE_DEFAULT",
            asset_name=name,
            link_method=link_method(get_browser_area(name)),
            at_mouse=True,
            asset_quality=quality,
            reload=reload,
        )


@handlers.persistent
def undo_post(scene, _):
    """If undo is called just after an asset has been imported, the asset will revert back to the original empty,
    which will be picked up by the depsgraph handler and have it's asset imported again,
    making it impossible to undo past that point.
    This prevents that by checking for any asset bridge empty and removing it
    before there is an update to the depsgraph"""
    # Hdris
    if (world := scene.world) and world.asset_bridge.is_dummy:
        bpy.data.worlds.remove(world)

    # Materials
    for obj in scene.objects:
        for slot in obj.material_slots:
            if (mat := slot.material) and mat.asset_bridge.is_dummy:
                bpy.data.materials.remove(mat)

    # Models
    obj_remove = []
    for obj in scene.objects:
        if obj.asset_bridge.is_dummy:
            obj_remove.append(obj)

    for obj in obj_remove:
        bpy.data.objects.remove(obj)


@handlers.persistent
def reset_import_state(_=None):
    """Forget references to datablocks from the previous file."""
    if bpy.app.timers.is_registered(_process_pending_imports):
        bpy.app.timers.unregister(_process_pending_imports)
    _pending_scene_names.clear()
    prev_materials.clear()
    prev_world.clear()


def register():
    for collection, callback in (
        (handlers.depsgraph_update_pre, depsgraph_update_pre_handler),
        (handlers.undo_post, undo_post),
        (handlers.load_pre, reset_import_state),
    ):
        if callback not in collection:
            collection.append(callback)


def unregister():
    reset_import_state()
    for collection, callback in (
        (handlers.depsgraph_update_pre, depsgraph_update_pre_handler),
        (handlers.undo_post, undo_post),
        (handlers.load_pre, reset_import_state),
    ):
        if callback in collection:
            collection.remove(callback)
