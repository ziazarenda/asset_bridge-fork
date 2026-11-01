from statistics import mean

import bpy
from bpy.props import StringProperty
from bpy.types import Object, Material, Operator

from ..settings import get_asset_settings
from ..constants import NODES


def set_real_world_mat_scale(material: Material, object: Object):
    """Set the real world scale of an asset bridge material based on the dimensions of the provided object"""
    size = mean(object.dimensions)
    node = material.node_tree.nodes[NODES.scale]
    asset_list_item = get_asset_settings(material).asset_list_item
    node.outputs[0].default_value = size / asset_list_item.ab_material_size


class AB_OT_set_real_world_mat_scale(Operator):
    """Set the real world scale of an asset bridge material based on the dimensions of the provided object"""
    bl_idname = "asset_bridge.set_real_world_mat_scale"
    bl_label = "Set real world material scale"
    bl_options = {"REGISTER"}

    material: StringProperty(name="material")
    object: StringProperty(name="object")

    def execute(self, context):
        material = bpy.data.materials.get(self.material)
        obj = bpy.data.objects.get(self.object)
        if material is None or obj is None:
            self.report({"ERROR"}, "The material or the object no longer exists")
            return {"CANCELLED"}
        set_real_world_mat_scale(material, obj)
        return {"FINISHED"}
