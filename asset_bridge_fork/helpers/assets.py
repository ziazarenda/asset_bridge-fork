import traceback
from uuid import uuid1
from typing import Callable

import bpy
from bpy.types import ID, World, Object, Context, Material, Collection, MaterialSlot
from mathutils import Vector as V

from .general import copy_bl_properties
from .library import get_dir_size
from .process import format_traceback
from ..settings import get_ab_settings, get_asset_settings, get_ab_scene_settings
from ..constants import ASSET_VERSIONS
from .main_thread import force_ui_update
from .downloads import DownloadJob
from ..apis.asset_types import Asset
from ..apis.asset_utils import HDRI
from ..operators.op_report_message import report_message
from ..operators.op_set_real_world_mat_scale import set_real_world_mat_scale

# Download directories include both the asset ID and quality. Different qualities
# must never share a task or import each other's incomplete files.
DOWNLOADING = {}
_download_jobs = {}
_import_timers = set()
_download_waiters = {}


def _start_timer(callback, interval=0.1):
    def tick():
        manager = getattr(bpy.context, "window_manager", None)
        if manager is not None and manager.is_interface_locked:
            return 0.1
        try:
            result = callback()
        except Exception:
            _import_timers.discard(tick)
            traceback.print_exc()
            return None
        if result is None:
            _import_timers.discard(tick)
        return result
    _import_timers.add(tick)
    bpy.app.timers.register(tick, first_interval=interval)


def prepare_and_download(asset, job):
    """Runs in the worker: fetch the asset's details, tell the job its size, then download."""
    asset.prepare()
    job.size = asset.get_download_size()
    asset.download_asset()


def download_asset(context, asset, draw=True, location=V(), reload=None):
    """Start file work in a worker; manage every Blender task on the main thread."""
    ab = get_ab_settings(context)
    list_item = asset.list_item
    key = str(asset.download_dir.resolve())
    task_name = DOWNLOADING.get(key)
    task = ab.tasks.get(task_name) if task_name else None
    if task is not None and not task.cancelled:
        if draw:
            bpy.ops.asset_bridge.draw_import_progress(
                "INVOKE_DEFAULT", task_name=task_name,
                location=location, asset_id=list_item.ab_idname,
            )
        return task_name

    task = ab.new_task(name=f"download_{list_item.ab_idname}_{uuid1()}")
    task_name = task.name
    try:
        if message := list_item.poll():
            raise ValueError(message)
        should_reload = ab.reload_asset if reload is None else reload
        # A worker can outlive a cancelled task or add-on disable. Reattach rather
        # than starting another writer in the same directory.
        job = _download_jobs.get(key)
        if job is not None and job.done.is_set():
            _download_jobs.pop(key, None)
            job = None
        if job is None and asset.is_downloaded and not should_reload:
            task.finish(remove=False)
            return task_name
        if job is None:
            if asset.is_ready():
                task.new_progress(asset.get_download_size())
                job = DownloadJob(asset.download_dir, asset.download_asset, asset.get_files())
                job.size = asset.get_download_size()
            else:
                # Some details (Poly Haven's file list) come from the internet. Get them in the
                # worker, and size the progress bar once they are known.
                task.new_progress(1).message = "Getting asset info..."
                job = DownloadJob(asset.download_dir, lambda: prepare_and_download(asset, job), asset.get_files())
            _download_jobs[key] = job
            job.start()
        else:
            task.new_progress(job.size or 1)
    except Exception as error:
        traceback.print_exc()
        task.cancel(remove=False)
        report_message("ERROR", f"Cannot download {list_item.ab_idname}: {error}")
        return task_name

    DOWNLOADING[key] = task_name
    if draw:
        bpy.ops.asset_bridge.draw_import_progress(
            "INVOKE_DEFAULT", task_name=task_name,
            location=location, asset_id=list_item.ab_idname,
        )

    def check_progress():
        task = ab.tasks.get(task_name)
        if not job.done.is_set():
            if task is not None and not task.cancelled and task.progress:
                if job.size and task.progress.max != job.size:
                    task.progress.max = job.size
                    task.progress.message = ""
                task.progress.progress = get_dir_size(job.directory)
                force_ui_update(area_types="VIEW_3D")
            return 0.1
        if _download_jobs.get(key) is job:
            _download_jobs.pop(key, None)
        if DOWNLOADING.get(key) == task_name:
            DOWNLOADING.pop(key, None)
        if task is not None and not task.cancelled:
            if job.error is not None:
                task.cancel(remove=False)
                print(job.traceback)
                report_message("ERROR", f"Error downloading {list_item.ab_idname}:\n{job.traceback}")
            else:
                task.finish(remove=False)
        force_ui_update(area_types="VIEW_3D")
        return None

    _start_timer(check_progress)
    return task_name


@bpy.app.handlers.persistent
def clear_import_timers(_=None):
    """Do not apply delayed imports to another .blend file or disabled add-on."""
    for callback in tuple(_import_timers):
        if bpy.app.timers.is_registered(callback):
            bpy.app.timers.unregister(callback)
    _import_timers.clear()
    DOWNLOADING.clear()
    _download_waiters.clear()
    # File workers cannot be forcibly killed. Retain them to prevent duplicate
    # writes if the add-on is reenabled while a request is still finishing.


def register():
    if clear_import_timers not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(clear_import_timers)


def unregister():
    clear_import_timers()
    if clear_import_timers in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(clear_import_timers)


def import_asset(context: Context, asset: Asset, location: V = V(), material_slot: MaterialSlot = None):
    """Import an asset while handling errors, and properties necessary for Asset Bridge to work properly.
    This modifies blend data, so it needs to be run in the main thread."""
    asset_list_item = asset.list_item
    imported = None
    if asset.list_item.ab_type == HDRI:
        from_world = context.scene.world
    try:
        imported = asset.import_asset(context)
        uuid = uuid1()

        def update_settings(data_block, index=0):
            settings = get_asset_settings(data_block)
            settings.is_asset_bridge = True
            settings.idname = asset_list_item.ab_idname
            settings.quality_level = asset.quality_level
            settings.uuid = str(uuid)
            settings.index = index
            if isinstance(data_block, World):
                settings.version = ASSET_VERSIONS.hdri
            elif isinstance(data_block, Material):
                settings.version = ASSET_VERSIONS.material
            elif isinstance(data_block, Collection) or isinstance(data_block, Object):
                settings.version = ASSET_VERSIONS.model

        update_settings(imported)

        if isinstance(imported, Material):
            if material_slot:
                material_slot.material = imported
                obj = material_slot.id_data
                obj.active_material_index = list(obj.material_slots).index(material_slot)

                # Set real world scale
                if get_ab_scene_settings(context).apply_real_world_scale:
                    set_real_world_mat_scale(imported, obj)

        elif isinstance(imported, World):
            if from_world:
                copy_bl_properties(from_world.cycles, imported.cycles)
                copy_bl_properties(from_world.cycles_visibility, imported.cycles_visibility)
        elif isinstance(imported, Collection):
            for i, obj in enumerate(imported.objects):
                update_settings(obj, index=i)
                obj.location += location
    except Exception as e:
        # This is needed so that the errors are shown to the user.
        traceback.print_exc()
        report_message("ERROR", f"Error importing asset {asset_list_item.ab_idname}:\n{format_traceback(e)}")
        return None
    bpy.ops.ed.undo_push()
    return imported


def download_and_import_asset(
    context: Context,
    asset: Asset,
    material_slot: MaterialSlot = None,
    draw: bool = True,
    location: V = V(),
    on_completion: Callable[[ID], None] = None,
    on_cancel: Callable = None,
    reload: bool = None,
):
    """Download and import an asset, taking care of errors, viewport progress etc.

    Args:
        context (Context): The context.
        asset (Asset): The Asset Bridge asset instance to import.
        material_slot (MaterialSlot, optional): if it is a material asset,
            then this is the material slot to apply the imported material to. Defaults to None.
        draw (bool, optional): Whether to draw the progress in the 3D viewport. Defaults to True.
        location (V, optional): The 3D Vector of the location to draw the progress at. Defaults to V().
        on_completion (Callable[[ID], None], optional): A function to call once the asset has been imported.
            Takes the imported asset as an argument. Defaults to None.
        on_cancel (Callable, optional): A function to call if something goes wrong during the import. Defaults to None.
    """

    ab = get_ab_settings(context)
    task_name = download_asset(context, asset, draw, location, reload=reload)

    _download_waiters[task_name] = _download_waiters.get(task_name, 0) + 1

    def release_task():
        remaining = _download_waiters.get(task_name, 1) - 1
        if remaining:
            _download_waiters[task_name] = remaining
        else:
            _download_waiters.pop(task_name, None)
            task = ab.tasks.get(task_name)
            if task is not None:
                task.finish()

    def check_download():
        task = ab.tasks.get(task_name)
        if task is None or task.cancelled:
            try:
                if on_cancel:
                    on_cancel()
            finally:
                release_task()
            return None
        if not task.finished:
            return 0.1
        try:
            imported = import_asset(context, asset, location, material_slot)
            if imported is not None:
                if on_completion:
                    on_completion(imported)
            elif on_cancel:
                on_cancel()
        finally:
            release_task()
        return None

    _start_timer(check_download)
