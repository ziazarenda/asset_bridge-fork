from bpy.types import Operator
from ..settings import get_ab_settings


class AB_OT_clear_task(Operator):
    """Clear all Asset Bridge tasks"""
    bl_idname = "asset_bridge.clear_task"
    bl_label = "Clear Task"
    bl_options = {"REGISTER"}

    def execute(self, context):
        ab = get_ab_settings(context)
        for task in ab.tasks:
            task.finish(remove=True)
        return {"FINISHED"}
