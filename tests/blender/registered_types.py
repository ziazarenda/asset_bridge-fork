"""Every operator, panel and menu keeps its name, label, options and properties.

The table was derived from the original @BOperator/@BPanel/@BMenu decorators (their naming
rules applied to each class), before the add-on moved to plain Blender classes. It guards
that migration: a class that is renamed, loses a property or changes its options fails here.
A property list of None means "not checked" (the operator builds its own).
"""
import os

import bpy

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

# idname: [class name (None = generated), label, options, property names]
OPERATORS = {
    "asset_bridge.cancel_task": [
        "AB_OT_cancel_task",
        "Cancel Task",
        [
            "REGISTER"
        ],
        [
            "name"
        ]
    ],
    "asset_bridge.check_for_new_assets": [
        "AB_OT_check_for_new_assets",
        "Check for new assets",
        [
            "REGISTER"
        ],
        [
            "auto_download",
            "report_message"
        ]
    ],
    "asset_bridge.clear_task": [
        "AB_OT_clear_task",
        "Clear Task",
        [
            "REGISTER"
        ],
        []
    ],
    "asset_bridge.create_ab_collection": [
        "AB_OT_create_ab_collection",
        "Create Asset Bridge collection",
        [
            "UNDO"
        ],
        []
    ],
    "asset_bridge.create_dummy_assets": [
        "AB_OT_create_dummy_assets",
        "Create Dummy Assets",
        [
            "REGISTER"
        ],
        []
    ],
    "asset_bridge.download_previews": [
        "AB_OT_download_previews",
        "Download Previews",
        [
            "REGISTER"
        ],
        [
            "reload",
            "test_number"
        ]
    ],
    "asset_bridge.draw_import_progress": [
        "AB_OT_draw_import_progress",
        "Draw Import Progress",
        [
            "REGISTER"
        ],
        [
            "asset_id",
            "location",
            "task_name"
        ]
    ],
    "asset_bridge.dummy": [
        "AB_OT_dummy",
        "Dummy",
        [
            "REGISTER"
        ],
        []
    ],
    "asset_bridge.import_asset": [
        "AB_OT_import_asset",
        "Import Asset",
        [
            "REGISTER"
        ],
        None
    ],
    "asset_bridge.initialize_asset_lists": [
        "AB_OT_initialize_asset_lists",
        "Get asset lists.",
        [
            "REGISTER",
            "UNDO"
        ],
        [
            "initialize_all"
        ]
    ],
    "asset_bridge.open_folder": [
        "AB_OT_open_folder",
        "Open Folder",
        [
            "REGISTER"
        ],
        [
            "file_path"
        ]
    ],
    "asset_bridge.open_log_file": [
        "AB_OT_open_log_file",
        "Open Log File",
        [],
        []
    ],
    "asset_bridge.open_ph_author_website": [
        "AB_OT_open_ph_author_website",
        "Open Ph Author Website",
        [
            "REGISTER"
        ],
        [
            "author_name"
        ]
    ],
    "asset_bridge.remove_task": [
        "AB_OT_remove_task",
        "Remove Task",
        [
            "REGISTER"
        ],
        [
            "name"
        ]
    ],
    "asset_bridge.report_message": [
        "AB_OT_report_message",
        "Report Message",
        [
            "REGISTER"
        ],
        [
            "message",
            "severity"
        ]
    ],
    "asset_bridge.set_real_world_mat_scale": [
        None,
        "Set real world material scale",
        [
            "REGISTER"
        ],
        [
            "material",
            "object"
        ]
    ],
    "asset_bridge.show_info": [
        "AB_OT_show_info",
        "Show Info",
        [
            "REGISTER"
        ],
        [
            "icon",
            "message",
            "show_content",
            "title",
            "width"
        ]
    ],
    "asset_bridge.show_popup": [
        "AB_OT_show_popup",
        "Show Popup",
        [
            "REGISTER"
        ],
        [
            "centered",
            "confirm",
            "confirm_op",
            "message",
            "severity",
            "title",
            "width"
        ]
    ],
    "asset_bridge.swap_asset": [
        "AB_OT_swap_asset",
        "Swap Asset",
        [
            "REGISTER"
        ],
        [
            "asset_id",
            "to_quality"
        ]
    ],
    "asset_bridge.toggle_tiling_preview": [
        "AB_OT_toggle_tiling_preview",
        "Toggle Tiling Preview",
        [
            "REGISTER"
        ],
        [
            "material_name"
        ]
    ],
    "asset_bridge.view_high_res_previews": [
        "AB_OT_view_high_res_previews",
        "View High Res Previews",
        [
            "REGISTER"
        ],
        []
    ]
}

# These must still accept a per-button description (op.bl_description = "...").
DYNAMIC_DESCRIPTION = {
    "asset_bridge.cancel_task",
    "asset_bridge.create_dummy_assets",
    "asset_bridge.open_folder",
    "asset_bridge.check_for_new_assets",
    "asset_bridge.download_previews",
    "asset_bridge.swap_asset",
}

# class name: [label, space, region, options]
PANELS = {
    "AB_PT_asset_info": [
        "Asset Info",
        "FILE_BROWSER",
        "TOOLS",
        []
    ],
    "AB_PT_asset_props_viewport": [
        "Asset settings",
        "VIEW_3D",
        "UI",
        []
    ]
}

# class name: label
MENUS = {
    "AB_MT_download_previews_menu": "Ab Mt Download Previews Menu",
    "AB_MT_swap_hdri_asset": "Swap HDRI quality",
    "AB_MT_swap_material_asset": "Swap material quality",
    "AB_MT_swap_model_asset": "Swap model quality"
}


def find_class(base, idname):
    """The registered Python class with this bl_idname (bpy.types has them under other names)."""
    found = [cls for cls in base.__subclasses__() if getattr(cls, "bl_idname", None) == idname]
    assert found, f"nothing registered as {idname}"
    return found[-1]


for idname, (class_name, label, options, props) in sorted(OPERATORS.items()):
    cls = find_class(bpy.types.Operator, idname)
    check(f"{idname}: idname", cls.bl_idname == idname)
    check(f"{idname}: label", cls.bl_label == label)
    check(f"{idname}: options {options}", sorted(getattr(cls, "bl_options", ())) == options)
    rna = getattr(getattr(bpy.ops, idname.split(".")[0]), idname.split(".")[1]).get_rna_type()
    names = sorted(p.identifier for p in rna.properties if p.identifier not in {"rna_type", "bl_description"})
    if props is not None:
        check(f"{idname}: properties {props}", names == props)
    if idname in DYNAMIC_DESCRIPTION:
        check(f"{idname}: per-button description", "bl_description" in rna.properties)

# Nothing extra is registered under this add-on's namespace.
registered = {n for n in dir(bpy.ops.asset_bridge) if not n.startswith("_")}
expected = {i.split(".")[1] for i in OPERATORS}
check(f"no unexpected operators {sorted(registered - expected)}", registered == expected)

for class_name, (label, space, region, options) in sorted(PANELS.items()):
    cls = find_class(bpy.types.Panel, class_name)
    check(f"{class_name}: label", cls.bl_label == label)
    check(f"{class_name}: space/region", (cls.bl_space_type, cls.bl_region_type) == (space, region))
    check(f"{class_name}: options", sorted(getattr(cls, "bl_options", ())) == options)

for class_name, label in sorted(MENUS.items()):
    cls = find_class(bpy.types.Menu, class_name)
    check(f"{class_name}: label", cls.bl_label == label)
    check(f"{class_name}: idname", cls.bl_idname == class_name)

print(f"ALL {checks} CHECKS PASSED")
