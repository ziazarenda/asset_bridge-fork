
from bpy.props import StringProperty
from bpy.types import Operator

from ..helpers.paths import open_local_path
from ..helpers.button_description import ButtonDescription, button_description


class AB_OT_open_folder(ButtonDescription, Operator):
    """Open a folder in the default file explorer"""
    bl_idname = "asset_bridge.open_folder"
    bl_label = "Open Folder"
    bl_options = {"REGISTER"}
    bl_description: button_description("Open a folder in the default file explorer")

    file_path: StringProperty(
        default=".",
        description="The path to the folder to open. By default this is the addon folder",
    )

    def execute(self, context):
        try:
            open_local_path(self.file_path)
        except (OSError, RuntimeError) as error:
            self.report({"ERROR"}, str(error))
            return {"CANCELLED"}
        return {"FINISHED"}
