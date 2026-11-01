from threading import Thread

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ...helpers import http
from ...helpers.main_thread import run_in_main_thread


class AB_OT_open_ph_author_website(Operator):
    """Open the website of the given author"""
    bl_idname = "asset_bridge.open_ph_author_website"
    bl_label = "Open Ph Author Website"
    bl_options = {"REGISTER"}

    author_name: StringProperty()

    def execute(self, context):
        # Imported here: the report operator imports modules that import this one
        from ...operators.op_report_message import report_message

        author = self.author_name

        def look_up():
            """Ask Poly Haven for the author's link without freezing the interface"""
            try:
                data = http.get_json(f"https://api.polyhaven.com/author/{author}", timeout=15)
            except OSError as error:
                report_message("ERROR", f"Could not look up {author}:\n{error}", main_thread=True)
                return

            if "link" in data:
                link = data["link"]
            elif "email" in data:
                link = "mailto:" + data["email"]
            else:
                report_message("WARNING", "No website found for this author", main_thread=True)
                return
            run_in_main_thread(bpy.ops.wm.url_open, kwargs={"url": link})

        Thread(target=look_up, daemon=True).start()
        return {"FINISHED"}
