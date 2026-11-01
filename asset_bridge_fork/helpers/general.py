from bpy.types import Property, PropertyGroup

from . import http


def copy_bl_properties(from_data_block: PropertyGroup, to_data_block: PropertyGroup, print_errors=False):
    """Copy all of the blender properties from one property group to another."""
    for prop in from_data_block.bl_rna.properties:
        if isinstance(prop, Property):
            try:
                setattr(to_data_block, prop.identifier, getattr(from_data_block, prop.identifier))
            except AttributeError as e:
                if print_errors:
                    print(prop, e)


def check_internet(url="https://www.google.com/", timeout=3):
    """Whether the internet can be reached. Blocks for up to `timeout` seconds when it cannot."""
    return http.is_online(url, timeout)
