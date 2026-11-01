"""Material and HDRI construction on this Blender version, with generated textures."""
import os
import tempfile
from pathlib import Path

import bpy

MODULE = os.environ["ADDON_MODULE"]

def ensure_enabled_in_preferences():
    """The test runner loads the add-on without listing it in the user's add-ons,
    as ticking its checkbox would. Do that part here: get_prefs() needs it."""
    if MODULE not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = MODULE


ensure_enabled_in_preferences()

asset_utils = __import__(MODULE + ".apis.asset_utils", fromlist=["x"])
constants = __import__(MODULE + ".constants", fromlist=["x"])
compat = __import__(MODULE + ".helpers.compatibility", fromlist=["x"])
checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


def make_texture(folder, name, color=(0.5, 0.5, 0.5, 1.0), ext="png"):
    image = bpy.data.images.new(name, 4, 4, alpha=True, float_buffer=(ext == "exr"))
    image.pixels = list(color) * 16
    path = Path(folder) / f"{name}.{ext}"
    image.filepath_raw = str(path)
    image.file_format = "OPEN_EXR" if ext == "exr" else "PNG"
    image.save()
    bpy.data.images.remove(image)
    return path


def linked_to(node, socket_name):
    return [link.from_node for link in node.inputs[socket_name].links]


with tempfile.TemporaryDirectory() as folder:
    maps = ["diffuse", "ao", "metalness", "roughness", "emission", "opacity", "normal", "displacement"]
    files = {name: make_texture(folder, name) for name in maps}

    # A full set of maps
    material = asset_utils.import_material(files, "TestFull", link_method="APPEND")
    check("material created", material.name == "TestFull")
    check("marked complete", bool(material.get("_ab_shader_complete")))

    nodes = material.node_tree.nodes
    bsdf = nodes[constants.NODES.principled_bsdf]
    check("principled node found", bsdf.type == "BSDF_PRINCIPLED")

    emission = compat.emission_input_name(bsdf)
    check("emission socket exists", emission in bsdf.inputs)
    check("emission texture linked", len(bsdf.inputs[emission].links) == 1)
    check("alpha linked", len(bsdf.inputs["Alpha"].links) == 1)
    check("metallic linked", len(bsdf.inputs["Metallic"].links) == 1)
    check("roughness linked through its group", len(bsdf.inputs["Roughness"].links) == 1)
    check("normal linked", len(bsdf.inputs["Normal"].links) == 1)
    check("base color linked (AO mix)", len(bsdf.inputs["Base Color"].links) == 1)

    output = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    check("displacement linked to output", len(output.inputs["Displacement"].links) == 1)
    check("displacement is muted by default", output.inputs["Displacement"].links[0].is_muted)
    check("mapping node present", constants.NODES.mapping in nodes)
    check("anti tiling group present and muted", nodes[constants.NODE_GROUPS.anti_tiling].mute)

    # Displacement method goes through the compatibility layer without raising.
    compat.set_displacement_method(material)
    compat.set_displacement_method(material, engine="BLENDER_EEVEE")
    check("displacement method set", True)

    # Only some maps
    small = asset_utils.import_material({"diffuse": files["diffuse"]}, "TestSmall", link_method="APPEND")
    small_bsdf = small.node_tree.nodes[constants.NODES.principled_bsdf]
    check("diffuse only: base color linked", len(small_bsdf.inputs["Base Color"].links) == 1)
    check("diffuse only: no normal", len(small_bsdf.inputs["Normal"].links) == 0)

    # Empty input is refused and leaves nothing behind
    before = len(bpy.data.materials)
    try:
        asset_utils.import_material({}, "TestEmpty")
        raised = False
    except ValueError:
        raised = True
    check("empty texture set refused", raised)
    check("nothing left behind", len(bpy.data.materials) == before)

    # A failing build removes its half-built material
    try:
        asset_utils.import_material({"diffuse": Path(folder) / "missing.png"}, "TestBroken", link_method="APPEND")
    except Exception:
        pass
    check("failed material is cleaned up", "TestBroken" not in bpy.data.materials)

    # HDRI
    hdri_file = make_texture(folder, "sky", color=(0.2, 0.4, 0.8, 1.0), ext="exr")
    world = asset_utils.import_hdri(hdri_file, "TestSky", link_method="APPEND")
    check("world created", world.name == "TestSky")
    check("environment texture present", any(n.type == "TEX_ENVIRONMENT" for n in world.node_tree.nodes))
    out = next(n for n in world.node_tree.nodes if n.type == "OUTPUT_WORLD")
    check("world output linked", len(out.inputs[0].links) == 1)

print(f"ALL {checks} CHECKS PASSED")
