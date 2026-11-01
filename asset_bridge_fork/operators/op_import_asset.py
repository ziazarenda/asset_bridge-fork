import bpy
from bpy.props import BoolProperty, EnumProperty, StringProperty, FloatVectorProperty, IntProperty
from bpy.types import Operator
from mathutils import Vector as V

from ..api import get_asset_lists
from ..constants import DIRS
from ..helpers.assets import download_and_import_asset
from ..helpers.drawing import point_under_mouse
from ..apis.asset_utils import HDRI, MATERIAL
from .op_report_message import report_message


class AB_OT_import_asset(Operator):
    """Download and import an asset selected in the Asset Browser."""

    bl_idname = "asset_bridge.import_asset"
    bl_label = "Import Asset"
    bl_options = {"REGISTER"}

    def invoke(self, context, event):
        self._mouse_region = V((event.mouse_region_x, event.mouse_region_y))
        self._mouse_window = V((event.mouse_x, event.mouse_y))
        return self.execute(context)

    asset_name: StringProperty(
        description="The name of the asset to import. Leave empty to import the currently selected asset",
        default="",
    )

    asset_quality: StringProperty(
        description="The quality of the asset to import. Leave empty to import the currently selected asset quality",
        default="",
    )

    reload: BoolProperty(
        description="Whether to redownload the asset, or to use the local version if it is available.",
        default=False,
    )

    location: FloatVectorProperty(
        description="The location to put the imported asset/where to draw the progress",
        default=(0, 0, 0),
    )

    at_mouse: BoolProperty(
        description="Whether to import the asset at the point underneath the mouse cursor, or instead at the 3d cursor",
        default=False,
    )

    link_method: EnumProperty(
        items=[
            ("LINK", "Link", "Link"),
            ("APPEND", "Append", "Append"),
            ("APPEND_REUSE", "Append reuse", "Append reuse"),
        ],
        default="APPEND_REUSE",
    )

    material_target: StringProperty(options={"HIDDEN"})
    material_slot_index: IntProperty(default=-1, options={"HIDDEN"})

    def execute(self, context):
        if not hasattr(DIRS, "assets"):
            self.report({"ERROR"}, "Set the library folder in Asset Bridge preferences first.")
            return {"CANCELLED"}
        # Find 3D coordinates of the point under the mouse cursor
        if self.at_mouse:
            if not hasattr(self, "_mouse_region"):
                self.report({"ERROR"}, "Mouse placement requires invoking the import operator.")
                return {"CANCELLED"}
            try:
                location = point_under_mouse(context, self._mouse_region, self._mouse_window)
            except ValueError:
                message = "Cannot import assets when the preferences window is active. \
                Blender is weird like that :(".replace(
                    "  ", ""
                )
                report_message("ERROR", message)
                return {"CANCELLED"}
        else:
            location = V(self.location)

        if location is None:
            return {"CANCELLED"}
        settings = context.window_manager.asset_bridge
        name = self.asset_name or settings.asset_idname
        quality = self.asset_quality or settings.asset_quality
        asset_list_item = get_asset_lists().all_assets.get(name)
        if asset_list_item is None:
            self.report({"ERROR"}, f"Asset is unavailable: {name}")
            return {"CANCELLED"}
        material_slot = None
        if self.material_target:
            obj = bpy.data.objects.get(self.material_target)
            if obj is None or not 0 <= self.material_slot_index < len(obj.material_slots):
                self.report({"ERROR"}, "The target object or material slot no longer exists.")
                return {"CANCELLED"}
            material_slot = obj.material_slots[self.material_slot_index]
        try:
            asset = asset_list_item.to_asset(quality, self.link_method)
        except Exception as error:
            self.report({"ERROR"}, f"Cannot prepare {name}: {error}")
            return {"CANCELLED"}

        if self.at_mouse and asset_list_item.ab_type in {HDRI, MATERIAL} and len(context.window_manager.windows) > 1:
            report_message(
                "WARNING",
                "Downloading hdris and materials may not work as expected when Blender has multiple windows open. \
                Blender is weird :(".replace(
                    "  ", ""
                ),
            )

        download_and_import_asset(
            context, asset, material_slot, draw=True, location=location,
            reload=self.reload or settings.reload_asset,
        )
        return {"FINISHED"}
