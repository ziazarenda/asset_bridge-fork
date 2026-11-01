# needs-window
"""The built-in GPU shaders the progress overlay and the preview viewer draw with exist on this
Blender version, and can draw a quad into an offscreen buffer."""
import os

import bpy
import gpu
from mathutils import Matrix
from gpu_extras.batch import batch_for_shader

MODULE = os.environ["ADDON_MODULE"]
checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


def ensure_enabled_in_preferences():
    if MODULE not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = MODULE


ensure_enabled_in_preferences()
drawing = __import__(MODULE + ".helpers.drawing", fromlist=["x"])
Shaders = drawing.Shaders

check("uniform color shader", isinstance(Shaders.UNIFORM_COLOR, gpu.types.GPUShader))
check("image shader", isinstance(Shaders.IMAGE, gpu.types.GPUShader))

# Draw a quad covering the whole buffer (clip space), offscreen, the way the overlay draws
offscreen = gpu.types.GPUOffScreen(16, 16)
with offscreen.bind():
    gpu.state.active_framebuffer_get().clear(color=(0.0, 0.0, 0.0, 1.0))
    shader = Shaders.UNIFORM_COLOR
    quad = batch_for_shader(shader, "TRIS", {"pos": ((-1, -1), (1, -1), (1, 1), (-1, 1))}, indices=((0, 1, 2), (2, 3, 0)))
    gpu.matrix.push()
    gpu.matrix.load_identity()
    gpu.matrix.push_projection()
    gpu.matrix.load_projection_matrix(Matrix.Identity(4))
    shader.bind()
    shader.uniform_float("color", (1.0, 0.0, 0.0, 1.0))
    quad.draw(shader)
    pixels = gpu.state.active_framebuffer_get().read_color(8, 8, 1, 1, 4, 0, "UBYTE")
    gpu.matrix.pop_projection()
    gpu.matrix.pop()
offscreen.free()
values = [int(v) for v in pixels.to_list()[0][0]]
check(f"the quad is drawn red {values}", values[0] > 200 and values[1] < 50 and values[2] < 50)

print(f"ALL {checks} CHECKS PASSED")
