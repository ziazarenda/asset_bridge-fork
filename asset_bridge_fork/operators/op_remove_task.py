from bpy.props import StringProperty
from bpy.types import Operator

from ..settings import AssetTask, get_ab_settings


class AB_OT_remove_task(Operator):
    """Remove an Asset Bridge task"""
    bl_idname = "asset_bridge.remove_task"
    bl_label = "Remove Task"
    bl_options = {"REGISTER"}

    name: StringProperty()

    def execute(self, context):
        if not self.name:
            raise ValueError("No task name specified")

        ab = get_ab_settings(context)
        task: AssetTask = ab.tasks[self.name]

        task.finish(remove=True)
        return {"FINISHED"}
