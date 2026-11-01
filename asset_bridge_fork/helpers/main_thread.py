import bpy
from queue import Empty, Queue
import traceback


# It's a bad idea to modify blend data in arbitrary threads,
# so if those threads want to do so, they can add a function to the queue
# which will then be executed on the main thread based on a timer
main_thread_queue = Queue()


_enabled = False


def main_thread_timer():
    """Drain queued calls on Blender's main thread; one bad call cannot stop others."""
    if not _enabled:
        return None
    manager = getattr(bpy.context, "window_manager", None)
    if manager is not None and manager.is_interface_locked:
        return 0.05
    # Bound each tick so a busy producer cannot block the UI indefinitely.
    for _ in range(100):
        try:
            func, args, kwargs = main_thread_queue.get_nowait()
        except Empty:
            break
        try:
            func(*args, **kwargs)
        except Exception:
            traceback.print_exc()
    return 0.05


def run_in_main_thread(function, args=(), kwargs=None):
    """Queue a call without touching Blender APIs from the calling thread."""
    if _enabled:
        main_thread_queue.put((function, args, {} if kwargs is None else kwargs))


@bpy.app.handlers.persistent
def clear_pending_calls(_=None):
    while True:
        try:
            main_thread_queue.get_nowait()
        except Empty:
            return


def register():
    global _enabled
    _enabled = True
    if not bpy.app.timers.is_registered(main_thread_timer):
        bpy.app.timers.register(main_thread_timer, first_interval=0.05, persistent=True)
    if clear_pending_calls not in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.append(clear_pending_calls)


def unregister():
    global _enabled
    _enabled = False
    if bpy.app.timers.is_registered(main_thread_timer):
        bpy.app.timers.unregister(main_thread_timer)
    if clear_pending_calls in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(clear_pending_calls)
    clear_pending_calls()


def update_prop(data, name, value):
    """Update a single blender property in the main thread"""
    run_in_main_thread(setattr, (data, name, value))


def ui_update_timer(area, area_types, region_types):
    """Update all given areas, in the main thread"""
    if not isinstance(area_types, set):
        area_types = {area_types}
    if not isinstance(region_types, set):
        region_types = {region_types}
    areas = []
    if area:
        areas = [area]
    else:
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type not in area_types:
                    continue
                areas.append(area)
    for area in areas:
        for region in area.regions:
            if region.type not in region_types:
                continue
            region.tag_redraw()
    bpy.context.workspace.status_text_set_internal(None)


def force_ui_update(area=None, area_types={"VIEW_3D", "PREFERENCES"}, region_types={"WINDOW", "UI"}):
    """Sometimes calling tag_redraw doesn't work, but doing it in a timer does"""
    run_in_main_thread(ui_update_timer, args=(area, area_types, region_types))
