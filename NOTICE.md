# Notice

**Asset Bridge Fork** is an unofficial fork of **Asset Bridge** by Andrew Stevenson
(<https://github.com/strike-digital/asset_bridge>), released under the same license,
GNU General Public License v3.0 or later (see `LICENSE`).

The original copyright header is kept in `asset_bridge_fork/__init__.py`. This fork is
not made, endorsed or supported by the original author. His name, logos and store
links are not used here; if you want to support him, look at his original project.

## What this fork changes

Starting point: a maintenance build of Asset Bridge 2.2.4 (patched for Blender 5.2 and
Python 3.14, see `docs/UPSTREAM_MAINTENANCE_NOTES.md`), then:

- Package renamed to `asset_bridge_fork`; the update source is this repository.
- The bundled updater is replaced by the shared auto-updater of blender-addon-kit.
- The bundled `requests` library is replaced by a small standard-library HTTP helper with
  timeouts. Poly Haven's file list is fetched in the download worker, not on Blender's main
  thread, so starting an import no longer freezes the interface.
- The `BOperator`/`BPanel`/`BMenu` wrapper layer is gone: plain Blender classes.
- Network and download work no longer blocks Blender: connection checks, the asset lists and
  the preview downloads run in worker threads, and Blender data is only changed on the main thread.
- Downloads are written atomically, and a failed reload puts the previous files back.
- The current quality is shown on the swap button in the 3D Viewport panel.
- Unused code is removed: the custom GPU shaders, the operator wrapper layer and dead operators.
- A build script that runs tests and installs the add-on into a clean Blender profile.
- Tests for the package and for Blender 5.2 behaviour (registering, materials, HDRIs).

## Third-party code

- `asset_bridge_fork/vendor/humanize`: MIT, from the updater.
- `asset_bridge_fork/addon_updater*.py`: CG-Cookie Blender-Addon-Updater, GPL v2 or later.
- `asset_bridge_fork/auto_load.py`: based on Jacques Lucke's auto_load.

Downloaded assets come from Poly Haven (CC0) and ambientCG (CC0).
