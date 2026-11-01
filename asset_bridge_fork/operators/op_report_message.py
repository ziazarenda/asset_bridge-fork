from functools import wraps

import bpy
from bpy.props import StringProperty
from bpy.types import Operator

from ..helpers.main_thread import run_in_main_thread
from ..helpers.process import format_traceback


class AB_OT_report_message(Operator):
    """Report a message at the bottom of the screen, and in the info editor.
    Useful for threads and scripts that aren't being executed inside operators"""
    bl_idname = "asset_bridge.report_message"
    bl_label = "Report Message"
    bl_options = {"REGISTER"}

    severity: StringProperty(default="INFO")

    message: StringProperty(default="")

    def invoke(self, context, event):
        r"""The report needs to be done in the modal function otherwise it wont show at the bottom of the screen
        for some reason ¯\_(ツ)_/¯"""  # noqa
        # We also need to add a timer to update the window to make sure that it shows up immediately,
        # rather than when the user moves their mouse.
        self.timer = context.window_manager.event_timer_add(0.001, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        context.window_manager.event_timer_remove(self.timer)
        self.report({self.severity}, self.message)
        return {"FINISHED"}


def report_message(severity="INFO", message="Message!", main_thread=False):
    if main_thread:
        run_in_main_thread(report_message, (severity, message, False))
    else:
        bpy.ops.asset_bridge.report_message("INVOKE_DEFAULT", severity=severity, message=str(message))


def report_exceptions(main_thread=False):
    """A decorator to automatically report exceptions in the UI, useful when working with separate threads."""
    def report_exceptions_decorator(func):
        @wraps(func)
        def with_reporting(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                report_message(
                    "ERROR",
                    f"An error occurred while executing function {func.__name__}:\n\n{format_traceback(e)}",
                    main_thread=main_thread,
                )
        return with_reporting
    return report_exceptions_decorator
