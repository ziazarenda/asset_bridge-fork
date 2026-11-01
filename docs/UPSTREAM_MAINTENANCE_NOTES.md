# Asset Bridge 2.2.5 — maintenance build 1

This is an unofficial maintenance fork of Andrew Stevenson's Asset Bridge,
based on the supplied `asset_bridge-2_2_4-log-fix(1).zip`. The original author
credit and GPL-3.0-or-later licensing are retained. This package includes the
Python source and the GPL text in `COPYING`.

The target for manual validation is Daniel's Linux Blender 5.2.2 installation
using Python 3.14. This build has **not** been run inside Blender here.

## Install

1. Keep the previous working ZIP so you can reinstall it if needed.
2. Disable Asset Bridge in Blender Preferences.
3. Use **Install from Disk** to install `asset_bridge-2_2_5-maintenance.zip`.
4. Restart Blender, then enable **Asset Bridge 2.2.5 (maintenance)** if needed.
5. Check the library folder in its preferences. If empty, choose your existing
   library folder; downloaded assets do not need to be deleted.

The module name stays `asset_bridge`, so this replaces the installed add-on.
The download-library format is unchanged. The original updater still points
to the upstream project; installing an upstream release can replace these
local maintenance changes.

## What changed

- The import and log operators now inherit directly from Blender's `Operator`.
  Material assignment uses an object name and slot index as normal operator
  properties, removing the import operator's shared `CustomProperty` state.
- `helpers/downloads.py` owns file cleanup, worker execution, completion and
  failure state. It has no Blender imports. It leaves an incomplete marker on
  failed downloads; import file lists ignore that marker and cache checks
  reject incomplete directories.
- `helpers/assets.py` coordinates download jobs with Blender tasks and import
  callbacks. Worker code no longer reads or modifies Blender task RNA, reports
  UI messages, or registers Blender timers. Jobs are keyed by download path,
  which includes quality. Multiple imports may wait for the same download.
- Missing and cancelled tasks stop importing. Failed imports no longer call
  success callbacks. Callback failures still release their task. The explicit
  reload argument is passed through to download handling.
- `helpers/main_thread.py` uses one registered queue timer. Worker callers only
  enqueue Python callables. Exceptions are printed without stopping later
  queued calls. Processing pauses while Blender's interface is locked.
- Import timers and queued calls are cleared when loading another file or
  disabling the add-on. Pending file downloads can finish without applying a
  delayed import. Reenabling the same loaded modules can reattach to a running
  download rather than create a second writer in its directory.
- `helpers/compatibility.py` holds displacement API differences and emission
  socket naming. The previously patched Cycles/Eevee displacement behavior is
  retained, including the Eevee `BOTH` method.
- `helpers/diagnostics.py` generates report text independently of the log
  operator. A missing library folder or malformed library-info JSON is recorded
  in the report. Opening a log or folder uses Blender's native path operator
  with a string path, including spaces and Unicode characters.
- Poly Haven file downloads propagate errors from their parallel workers.
  Model subprocesses check their exit status; captured Poly Haven output is
  drained with `communicate()` to avoid waiting on a full output pipe.
- File downloads have connection/read timeouts. This is not an overall deadline.
- Class registration honors current deferred RNA pointer dependencies and
  reports dependency cycles instead of looping. Dependency order takes priority
  over explicit registration hints. Module cleanup runs before class teardown.
- Drag/drop snapshots reset on file loads; previous worlds are tracked per
  scene. Preferences initialization uses a named timer that can be cancelled
  during teardown. Two invalid string escapes were cleaned up.

## Existing compatibility patches retained

The uploaded archive's Python 3.14 annotation fix, class cache-path descriptor,
RNA-backed library preference, library-path restoration, deferred drag/drop
import, ambientCG texture-map parsing, modern material displacement/emission/
transparency handling, incomplete shader cleanup and improved traceback
reporting remain in the source.

Cached catalog data, previews, resources and bundled dependencies are included
in the install ZIP. Generated Python bytecode is excluded.

## Code map

| Work | Entry point |
| --- | --- |
| User starts import | `operators/op_import_asset.py` |
| Drag/drop detection | `handlers.py` |
| Download/import coordination | `helpers/assets.py` |
| File worker and result | `helpers/downloads.py` |
| Main-thread queue | `helpers/main_thread.py` |
| Provider URLs and file interpretation | `apis/ambient_cg`, `apis/polyhaven` |
| Shader construction | `apis/asset_utils.py` |
| Material API differences | `helpers/compatibility.py` |
| Diagnostic text / local opening | `helpers/diagnostics.py`, `helpers/paths.py` |

## Validation

The accompanying developer ZIP contains the source, tests, a patch against the
uploaded version and the test output. From that ZIP's extracted root, run:

```sh
python3 -m unittest discover -s tests -v
```

**32 tests pass under Python 3.12.** They import production modules with a small
Blender test double instead of registering the full add-on. Coverage includes
real temporary-file downloads on worker threads, failure markers, cleanup
errors, worker exception propagation, task cancellation, removed tasks, shared
downloads, separate qualities, reload, callback cleanup, queue lifecycle,
registration dependencies, path opening, diagnostics and material API branches.
All 96 Python source files compile under Python 3.12 without warnings.

These checks do not exercise actual Blender RNA registration, drawing, node
evaluation, live provider services or real model subprocesses. Python 3.14
execution has not been tested here.

## Check in Blender 5.2.2

1. Enable the add-on and confirm the existing library folder is restored.
2. Import an ambientCG 1K material, then a Poly Haven material.
3. Drop the same uncached material on two objects before its download finishes.
   Confirm both objects receive it. Try two different quality levels too.
4. Test the reload checkbox and cancel an in-progress import.
5. Import an HDRI and a model from each provider where offered.
6. Check displacement off/on in Eevee and Cycles on a subdivided mesh, and check
   the anti-tiling switch. These shader behaviors are intended to match your
   working patched version.
7. Open the diagnostic log and a folder from the add-on.
8. Save/reopen the file and check persistence. Disable/enable the add-on after
   downloads finish, checking the console for registration or timer errors.
9. Check undo after material, world and model drag/drop.

## Boundaries

This refactor targets import/download coordination and related diagnostics.
Most panels, shader construction, catalog/preview building, the updater and
the general `BOperator`/`BPanel` framework remain. The old bundled Requests
compatibility warning may still appear with the distribution's newer urllib3.

Cancelling an import prevents application to the scene; it does not forcibly
terminate HTTP work or a model-building process. Completed files may remain
cached. File replacement during reload is not transactional: failed reloads
leave a marker and need a retry. Hard process termination may leave partial
files too. Avoid manually reloading Python modules while downloads are running.

Provider construction/catalog metadata can still perform synchronous network
work, and provider model preparation still uses the existing Blender subprocess
helper. The complete provider layer is not independent of Blender yet.
Multi-window placement and switching scenes during a download still need
interactive validation. `PACK` still maps to independent append behavior;
texture packing remains governed by the add-on's Auto Pack Files setting.

Upstream source: https://github.com/strike-digital/asset_bridge

API references checked for this change:

- https://docs.blender.org/api/5.2/bpy.ops.wm.html#bpy.ops.wm.path_open
- https://docs.blender.org/api/5.0/bpy.app.timers.html

## Known limitations

- Swapping the quality of a model (`operators/op_swap_asset.py`) copies the
  location, rotation and scale from the old objects to the new ones by matching
  the order in which the objects were imported. If a model's object order ever
  differs between quality levels, the objects could be put in the wrong place.
- Model imports support appending and linking; there is no separate
  "append and reuse" mode for objects.
