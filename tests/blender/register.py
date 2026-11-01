"""The add-on registers, exposes its pieces, and unregisters without leftovers."""
import os

import addon_utils
import bpy

MODULE = os.environ["ADDON_MODULE"]
checks = 0


def ensure_enabled_in_preferences():
    """The test runner loads the add-on without listing it in the user's add-ons,
    as ticking its checkbox would. Do that part here: get_prefs() needs it."""
    if MODULE not in bpy.context.preferences.addons:
        bpy.context.preferences.addons.new().module = MODULE


ensure_enabled_in_preferences()


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


def has_ops(namespace, name):
    return hasattr(getattr(bpy.ops, namespace), name)


def snapshot():
    return {
        "ops": [n for n in dir(bpy.ops.asset_bridge) if not n.startswith("_")] if hasattr(bpy.ops, "asset_bridge") else [],
        "wm": hasattr(bpy.types.WindowManager, "asset_bridge"),
        "scene": hasattr(bpy.types.Scene, "asset_bridge"),
        "material": hasattr(bpy.types.Material, "asset_bridge"),
    }


loaded = snapshot()
check("operators registered", len(loaded["ops"]) >= 10)
check("import operator exists", has_ops("asset_bridge", "import_asset"))
check("log operator exists", has_ops("asset_bridge", "open_log_file"))
check("window manager settings", loaded["wm"])
check("scene settings", loaded["scene"])
check("material settings", loaded["material"])

prefs = bpy.context.preferences.addons[MODULE].preferences
check("preferences available", prefs is not None)
check("library path is a string", isinstance(prefs.lib_path_storage, str))
check("updater settings on preferences", hasattr(prefs, "auto_check_update") and hasattr(prefs, "updater_interval_days"))

# A fresh install has no cached catalog, so no icons are loaded yet. Drawing the
# preferences asks every list for its icon: it has to load on demand.
from types import SimpleNamespace

for module_name, class_name, prefix in (
    (".apis.ambient_cg.acg_asset_list", "ACG_AssetList", "acg"),
    (".apis.polyhaven.ph_asset_list", "PH_AssetList", "ph"),
):
    module = __import__(MODULE + module_name, fromlist=["x"])
    asset_list = object.__new__(getattr(module, class_name))
    asset_list.assets = {"first": SimpleNamespace(ab_prefix=prefix)}
    check(f"{prefix}: logo file ships with the add-on", asset_list.icon_path.exists())
    check(f"{prefix}: icon loads on demand", isinstance(asset_list.icon, int) and asset_list.icon > 0)

# Disable and enable again: nothing may be left registered, nothing may raise.
addon_utils.disable(MODULE, default_set=False)
gone = snapshot()
check("operators removed on disable", len(gone["ops"]) == 0)
check("properties removed on disable", not (gone["wm"] or gone["scene"] or gone["material"]))

again = addon_utils.enable(MODULE, default_set=False, persistent=False)
check("enables a second time", again is not None)
ensure_enabled_in_preferences()
back = snapshot()
check("operators back after re-enable", len(back["ops"]) == len(loaded["ops"]))
check("properties back after re-enable", back["wm"] and back["scene"] and back["material"])

print(f"ALL {checks} CHECKS PASSED")
