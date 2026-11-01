import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..helpers.main_thread import run_in_main_thread
from ..helpers.button_description import ButtonDescription, button_description
from ..settings import AssetTask, get_ab_settings


class AB_OT_cancel_task(ButtonDescription, Operator):
    """Cancel an Asset Bridge task"""
    bl_idname = "asset_bridge.cancel_task"
    bl_label = "Cancel Task"
    bl_options = {"REGISTER"}
    bl_description: button_description("Cancel an Asset Bridge task")

    name: StringProperty()

    def execute(self, context):
        if not self.name:
            raise ValueError("No task name specified")

        ab = get_ab_settings(context)
        task: AssetTask = ab.tasks.get(self.name)
        if task is None:
            # Already finished or cancelled, e.g. a second click on the cancel button.
            return {"CANCELLED"}
        if not task.progress:
            raise ValueError(f"Task '{self.name}' has no progress")

        task.cancel(remove=True)
        return {"FINISHED"}


def cancel_task(name: str, main_thread=False):
    if main_thread:
        run_in_main_thread(cancel_task, (name, False))
    else:
        return bpy.ops.asset_bridge.cancel_task("INVOKE_DEFAULT", name=name)
