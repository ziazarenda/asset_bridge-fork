from threading import Thread

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator

from ..api import get_asset_lists
from ..constants import PREVIEW_DOWNLOAD_TASK_NAME
from ..helpers.main_thread import run_in_main_thread, force_ui_update
from ..settings import get_ab_settings


class AB_OT_initialize_asset_lists(Operator):
    """Re initialize all asset lists with data from the internet rather than from the cache"""
    bl_idname = "asset_bridge.initialize_asset_lists"
    bl_label = "Get asset lists."
    bl_options = {"REGISTER", "UNDO"}

    initialize_all: BoolProperty(default=False)

    def execute(self, context):
        lists_obj = get_asset_lists()
        asset_lists = lists_obj.asset_lists

        # Shown in the same place as the preview download that follows
        task = get_ab_settings(context).new_task(name=PREVIEW_DOWNLOAD_TASK_NAME)
        task.new_progress(1).message = "Getting the asset lists..."
        force_ui_update()

        names = [n for n in asset_lists if self.initialize_all or not lists_obj.is_initialized(n)]

        def get_lists():
            # Waiting for the server must not freeze the interface, so this runs off the main thread
            threads = [Thread(target=lists_obj.initialize_asset_list, args=[n]) for n in names]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()

            run_in_main_thread(task.finish)
            # Failures were already reported by initialize_asset_list
            if lists_obj.all_initialized:
                run_in_main_thread(bpy.ops.asset_bridge.download_previews)

        Thread(target=get_lists).start()
        return {"FINISHED"}
