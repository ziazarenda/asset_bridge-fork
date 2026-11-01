"""Let a button give an operator its own tooltip.

Add `ButtonDescription` as the first base class and a `bl_description` property:

    class AB_OT_example(ButtonDescription, Operator):
        \"\"\"Fallback tooltip\"\"\"
        bl_description: button_description("Fallback tooltip")

then a button can say `op = layout.operator(...); op.bl_description = "Specific tooltip"`.
"""
from bpy.props import StringProperty


def button_description(default):
    """The hidden property that carries the tooltip of one button."""
    return StringProperty(default=default, options={"HIDDEN"})


class ButtonDescription:
    @classmethod
    def description(cls, context, properties):
        return properties.bl_description if properties else (cls.__doc__ or cls.bl_label)
