from bpy.types import Operator


class AB_OT_dummy(Operator):
    """Do nothing, sometimes useful for UI stuff."""
    bl_idname = "asset_bridge.dummy"
    bl_label = "Dummy"
    bl_options = {"REGISTER"}

    def execute(self, context):
        return {"FINISHED"}
