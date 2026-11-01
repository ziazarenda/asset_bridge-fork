from bpy.types import Operator

from ..api import get_asset_lists
from ..constants import DIRS, FILES
from ..helpers.diagnostics import build_diagnostic_report
from ..helpers.paths import open_local_path


class AB_OT_open_log_file(Operator):
    """Write diagnostics and open the log in its default application."""

    bl_idname = "asset_bridge.open_log_file"
    bl_label = "Open Log File"

    def execute(self, context):
        try:
            output = build_diagnostic_report(get_asset_lists(), DIRS, FILES)
            FILES.log.parent.mkdir(parents=True, exist_ok=True)
            FILES.log.write_text(output, encoding="utf-8")
            open_local_path(FILES.log)
        except (OSError, RuntimeError) as error:
            self.report({"ERROR"}, f"Cannot open the diagnostic log: {error}")
            return {"CANCELLED"}
        return {"FINISHED"}
