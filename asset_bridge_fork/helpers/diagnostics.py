# SPDX-License-Identifier: GPL-3.0-or-later
"""Build diagnostic text independently of Blender operators and UI contexts."""

import json


def build_diagnostic_report(asset_lists, dirs, files):
    lines = ["Asset Bridge maintenance build 1", "", "Asset lists:"]
    for asset_list in asset_lists.values():
        lines.append(f"  {asset_list.name}:")
        try:
            initialized = asset_lists.is_initialized(asset_list.name)
            lines.append(f"    initialized: {initialized}")
            if initialized:
                lines.append(f"    assets: {len(asset_list.assets)}")
            cache = asset_list.data_cache_file
            lines.append(f"    cache: {cache}")
            lines.append(f"    cache bytes: {cache.stat().st_size if cache.is_file() else 'missing'}")
        except (OSError, AttributeError, ValueError) as error:
            lines.append(f"    Cannot inspect asset list: {error}")

    lines.extend(["", f"No. of assets: {len(asset_lists.all_assets)}",
                  f"No. of previews: {len(list(dirs.previews.glob('*.png')))}"])
    info = getattr(files, "lib_info", None)
    if info is not None and info.is_file():
        try:
            version = json.loads(info.read_text(encoding="utf-8"))["version"]
            lines.append(f"Library version: {version}")
        except (OSError, ValueError, KeyError, TypeError) as error:
            lines.append(f"Cannot read library info: {error}")
    else:
        lines.append("No library info file found.")

    dummy_dir = getattr(dirs, "dummy_assets", None)
    if dummy_dir is None or not dummy_dir.is_dir():
        lines.append(f"Dummy assets folder is unavailable: {dummy_dir or 'not configured'}")
        return "\n".join(lines) + "\n"

    lines.extend(["", "Asset Blends:"])
    for path in sorted(dummy_dir.glob("*.blend")):
        try:
            lines.append(f"  {path.name}: {path.stat().st_size} bytes")
        except OSError as error:
            lines.append(f"  {path.name}: {error}")
    lines.extend(["", "Catalog info:"])
    for path in sorted(dummy_dir.glob("*.cats.txt")):
        try:
            entries = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
            count = sum(bool(line) and not line.startswith(("#", "VERSION")) for line in entries)
            lines.append(f"  {path.name}: {count} catalogs")
        except (OSError, UnicodeError) as error:
            lines.append(f"  Cannot read {path.name}: {error}")
    lines.extend(["", "Asset Logs:"])
    for path in sorted(dummy_dir.glob("*_log.txt")):
        lines.append(f"  {path.name}:")
        try:
            lines.extend("    " + line for line in path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError as error:
            lines.append(f"    Cannot read log: {error}")
    return "\n".join(lines) + "\n"
