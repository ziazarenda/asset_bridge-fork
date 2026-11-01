import bpy
from bpy.types import Context, Operator

from ..settings import get_ab_scene_settings
from ..constants import AB_COLLECTION_NAME


class AB_OT_create_ab_collection(Operator):
    """Create a collection to import asset bridge models to."""
    bl_idname = "asset_bridge.create_ab_collection"
    bl_label = "Create Asset Bridge collection"
    bl_options = {"UNDO"}

    def execute(self, context: Context):
        collection = bpy.data.collections.get(AB_COLLECTION_NAME)
        if not collection:
            collection = bpy.data.collections.new(AB_COLLECTION_NAME)
            collection.color_tag = "COLOR_02"

        if AB_COLLECTION_NAME not in context.scene.collection.children:
            context.scene.collection.children.link(collection)
        ab_scene = get_ab_scene_settings(context)
        ab_scene.import_collection = collection
        return {"FINISHED"}
