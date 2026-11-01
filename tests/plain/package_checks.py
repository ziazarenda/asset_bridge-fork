"""Static checks on the add-on package. No Blender needed.

    python tests/plain/package_checks.py
"""
import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ADDON = ROOT / "asset_bridge_fork"
checks = 0


def check(name, condition):
    global checks
    assert condition, name
    checks += 1
    print("PASS:", name)


sources = {p: p.read_text(encoding="utf-8") for p in ADDON.rglob("*.py") if "vendor" not in p.parts}

# Every file parses.
for path, text in sources.items():
    ast.parse(text, str(path))
check(f"{len(sources)} files parse", True)

# bl_info is readable without importing the add-on.
tree = ast.parse(sources[ADDON / "__init__.py"])
info = next(ast.literal_eval(node.value) for node in tree.body
            if isinstance(node, ast.Assign) and node.targets[0].id == "bl_info")
check("bl_info has a 3-number version", len(info["version"]) == 3)
check("bl_info names the original author", "Andrew Stevenson" in info["author"])
check("bl_info does not claim the original name", info["name"] != "Asset Bridge")

# Updater settings point at this repo and match the folder name.
constants = sources[ADDON / "constants.py"]
for key, value in {"ADDON_ID": ADDON.name, "GITHUB_REPO": "asset_bridge-fork"}.items():
    check(f"constants.{key}", re.search(rf'^{key}\s*=\s*"{re.escape(value)}"', constants, re.M))
check("constants.GITHUB_USER set", re.search(r'^GITHUB_USER\s*=\s*"[^"]+"', constants, re.M))
check("constants.GITHUB_BRANCH set", re.search(r'^GITHUB_BRANCH\s*=\s*"[^"]+"', constants, re.M))

# Nothing may import the add-on by its old absolute name: the folder is not called that.
bad = [str(p.relative_to(ROOT)) for p, t in sources.items() if re.search(r"^\s*(from|import)\s+asset_bridge\b", t, re.M)]
check(f"no absolute imports of the old module name {bad}", not bad)

# The wrapper layer over Blender's classes is gone: plain Operator/Panel/Menu classes only.
for needle in ("btypes", "BOperator", "BPanel", "BMenu", "FunctionToOperator", "BOperator.type"):
    users = [str(p.relative_to(ROOT)) for p, t in sources.items() if needle in t]
    check(f"nothing uses {needle} {users}", not users)

# Every operator names itself (bl_idname) in this add-on's namespace.
for path, text in sources.items():
    for match in re.finditer(r"^class (AB_OT_\w+)\(", text, re.M):
        check(f"{match.group(1)} has an idname", re.search(r'^    bl_idname = "asset_bridge\.\w+"', text, re.M))

# The bundled `requests` is gone: all network access goes through helpers/http.py.
check("vendor/requests is removed", not (ADDON / "vendor" / "requests").exists())
users = [str(p.relative_to(ROOT)) for p, t in sources.items() if re.search(r"\brequests\b\s*(\.|import)|import requests|vendor.*requests", t)]
check(f"nothing imports requests {users}", not users)
check("the HTTP helper has no Blender import", "import bpy" not in sources[ADDON / "helpers" / "http.py"])

# Blender inspects the arguments of these methods when it registers a class, so a decorator
# that wraps them in (*args, **kwargs) breaks registration ("invoke ... to have 3 args").
BLENDER_METHODS = {"invoke", "modal", "execute", "draw", "poll", "check", "cancel"}
for path, text in sources.items():
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.ClassDef):
            for method in node.body:
                if isinstance(method, ast.FunctionDef) and method.name in BLENDER_METHODS:
                    decorators = [ast.unparse(d) for d in method.decorator_list]
                    check(f"{node.name}.{method.name} is not wrapped by {decorators}",
                          all(d in {"classmethod", "staticmethod"} for d in decorators))

# The original author's store, social and review links are not ours.
everything = "\n".join(sources.values())
for needle in ("blendermarket.com", "twitter.com", "blenderartists.org", "StrikeDigital"):
    check(f"no link to {needle}", needle not in everything)
# The only place his repo may appear: the credit in the preferences.
check("upstream credited in preferences", "strike-digital/asset_bridge" in sources[ADDON / "preferences.py"])
check("no leftover upstream updater target",
      "strike-digital" not in sources[ADDON / "addon_updater_ops.py"])

# The license and the original header stay.
check("GPL text present", "GNU GENERAL PUBLIC LICENSE" in (ROOT / "LICENSE").read_text())
check("GPL header kept in __init__", "GNU General Public License" in sources[ADDON / "__init__.py"])

print(f"ALL {checks} CHECKS PASSED")
