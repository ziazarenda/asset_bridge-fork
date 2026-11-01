import bpy
from bpy.types import ID, Menu, UILayout

from ..api import get_asset_lists
from ..settings import get_ab_settings, get_asset_settings
from ..apis.asset_types import AssetListItem
from ..operators.op_swap_asset import AB_OT_swap_asset


def draw_swap_op(layout: UILayout, asset_list_item: AssetListItem, qlevel_id: str, qlevel_label: str):
    icon = "CHECKMARK" if asset_list_item.is_downloaded(qlevel_id) else "IMPORT"
    op: AB_OT_swap_asset = layout.operator("asset_bridge.swap_asset", text=qlevel_label, icon=icon)
    op.bl_description = f"Change this asset's quality level to {qlevel_label}"
    op.to_quality = qlevel_id
    op.asset_id = asset_list_item.ab_idname


def current_quality_text(data_block: ID) -> str:
    """The quality level of an asset without its file size, e.g. "1k jpg", for labelling the swap button"""
    settings = get_asset_settings(data_block) if data_block else None
    asset = get_asset_lists().all_assets.get(settings.idname) if settings and settings.is_asset_bridge else None
    if asset is None:
        return ""
    for level_id, level_label, _ in asset.ab_quality_levels:
        if level_id == settings.quality_level:
            return level_label.split(" (")[0]
    return ""


def draw_swap_menu_button(layout: UILayout, menu_idname: str, data_block: ID):
    """Draw a button showing the current quality, which opens the given swap menu.
    A menu button would add a dropdown arrow, so this is a plain button that calls the menu."""
    text = current_quality_text(data_block)
    if not text:
        return
    button = layout.row()
    button.alignment = "RIGHT"  # only as wide as the text
    button.emboss = "NORMAL"
    button.operator("wm.call_menu", text=text).name = menu_idname


def draw_asset_levels(data_block: ID, layout: UILayout, label: str = "Change quality level", icon="NONE"):
    row = layout.row(align=True)
    # row.alignment = "EXPAND"
    row.label(text=label, icon=icon)

    layout.separator()
    settings = get_asset_settings(data_block)
    asset_name = settings.idname
    asset = get_asset_lists().all_assets[asset_name]
    for level_id, level_label, _ in asset.ab_quality_levels:
        row = layout.row(align=True)
        if settings.quality_level == level_id:
            row.enabled = False
        draw_swap_op(row, asset, level_id, level_label)
    layout.separator()
    ab = get_ab_settings(bpy.context)
    layout.prop(ab, "reload_asset", text="Redownload assets", icon="FILE_REFRESH")


class AB_MT_swap_hdri_asset(Menu):
    bl_idname = "AB_MT_swap_hdri_asset"
    bl_label = "Swap HDRI quality"

    @classmethod
    def poll(self, context):
        return context.scene.world is not None

    def draw(self, context):
        draw_asset_levels(context.scene.world, self.layout, label="Change HDRI quality", icon="WORLD")


class AB_MT_swap_material_asset(Menu):
    bl_idname = "AB_MT_swap_material_asset"
    bl_label = "Swap material quality"

    @classmethod
    def poll(self, context):
        if not context.object:
            return False
        if not get_asset_settings(context.object.active_material).is_asset_bridge:
            return False
        return context.object.active_material is not None

    def draw(self, context):
        draw_asset_levels(context.object.active_material, self.layout, label="Change material quality", icon="MATERIAL")


class AB_MT_swap_model_asset(Menu):
    bl_idname = "AB_MT_swap_model_asset"
    bl_label = "Swap model quality"

    @classmethod
    def poll(self, context):
        if not context.object:
            return False
        if not get_asset_settings(context.object).is_asset_bridge:
            return False
        return True

    def draw(self, context):
        draw_asset_levels(context.object, self.layout, label="Change model quality", icon="MESH_DATA")
