import bpy
from bpy.props import StringProperty
from bpy.types import Operator
from mathutils import Vector

from ..constants import NODES


class AB_OT_toggle_tiling_preview(Operator):
    """Toggle a preview of the anti tiling effect, to make it easier to see the different segments"""
    bl_idname = "asset_bridge.toggle_tiling_preview"
    bl_label = "Toggle Tiling Preview"
    bl_options = {"REGISTER"}

    material_name: StringProperty()

    def execute(self, context):
        material = bpy.data.materials[self.material_name]
        nodes = material.node_tree.nodes
        if out_node := nodes.get(NODES.temp_output):
            nodes.remove(out_node)
            return {"FINISHED"}

        tiling_node = nodes.get(NODES.anti_tiling)
        if tiling_node:
            out_node = nodes.new("ShaderNodeOutputMaterial")
            out_node.name = NODES.temp_output
            out_node.label = NODES.temp_output
            out_node.location = tiling_node.location + Vector((0, 140))
            out_node.is_active_output = True
            material.node_tree.links.new(tiling_node.outputs[-1], out_node.inputs[0])
        return {"FINISHED"}
