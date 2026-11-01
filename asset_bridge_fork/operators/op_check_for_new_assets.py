from threading import Thread

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator

from ..helpers.button_description import ButtonDescription, button_description
from ..api import get_asset_lists
from ..settings import get_ab_settings
from ..constants import CHECK_NEW_ASSETS_TASK_NAME
from ..helpers.general import check_internet
from .op_report_message import report_exceptions, report_message
from ..helpers.main_thread import force_ui_update


class AB_OT_check_for_new_assets(ButtonDescription, Operator):
    """Re download the asset lists and check for new assets"""
    bl_idname = "asset_bridge.check_for_new_assets"
    bl_label = "Check for new assets"
    bl_options = {"REGISTER"}
    bl_description: button_description("Re download the asset lists and check for new assets")

    report_message: BoolProperty(default=True)

    auto_download: BoolProperty(default=False, description="Whether to automatically download newly found previews")

    def execute(self, context):
        lists_obj = get_asset_lists()
        task = get_ab_settings(context).new_task(name=CHECK_NEW_ASSETS_TASK_NAME)
        progress = task.new_progress(max_steps=1)
        progress.message = "Connecting to the server..."
        # The timer runs after this operator has finished, so keep its settings now
        show_messages = self.report_message
        auto_download = self.auto_download

        # Checking the connection can take seconds, so it happens in a thread. The timer below
        # shows the progress, and starts the real work once the answer is known.
        connection = {"offline": False, "error": None, "threads": None}

        def connect():
            try:
                if check_internet():
                    connection["threads"] = lists_obj.initialize_all(blocking=False)
                else:
                    connection["offline"] = True
            except Exception as error:
                connection["error"] = error

        Thread(target=connect, daemon=True).start()
        sized = False

        @report_exceptions(main_thread=False)
        def finish():
            nonlocal sized

            if task.cancelled:
                report_message("INFO", "Cancelled checking for new assets")
                task.finish()
                return

            if connection["offline"]:
                report_message("ERROR", "Can't check for new assets, no internet connection detected")
                task.finish()
                return

            if connection["error"] is not None:
                task.finish()
                raise connection["error"]

            threads = connection["threads"]
            if threads is None:
                return 0.1

            if not sized:
                task.progress.max = max(len(threads), 1)
                sized = True

            finished = 0
            for thread in threads:
                if not thread.is_alive():
                    finished += 1

            if finished < len(threads):
                alive = [t for t in threads if t.is_alive()]
                if alive:
                    label = get_asset_lists()[alive[0].name].label
                    task.update_progress(
                        finished,
                        message=f"Getting asset list from {label} ({finished + 1}/{len(threads)})",
                    )
                return 0.1

            task.finish()
            new_assets = lists_obj.new_assets_available()
            if new_assets:
                if show_messages:
                    suffix = "s" if new_assets > 1 else ""
                    are = "are" if new_assets > 1 else "is"
                    report_message("INFO", f"There {are} {new_assets} new asset{suffix} to download.")
                    if auto_download:
                        bpy.ops.asset_bridge.download_previews()
            else:
                if show_messages:
                    report_message("INFO", "No new assets found, you're up to date!")
                if auto_download:
                    bpy.ops.asset_bridge.create_dummy_assets()

            force_ui_update(area_types={"PREFERENCES"})

        bpy.app.timers.register(finish)
        return {"FINISHED"}
