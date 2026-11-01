# SPDX-License-Identifier: GPL-3.0-or-later
"""Blender API differences used by material construction and its UI."""


EEVEE_ENGINES = {"BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"}


def supports_material_displacement(context, material):
    engine = context.scene.render.engine
    return engine == "CYCLES" or (
        engine in EEVEE_ENGINES and hasattr(material, "displacement_method")
    )


def set_displacement_method(material, method="DISPLACEMENT", engine=None):
    if engine in EEVEE_ENGINES:
        method = "BOTH"
    settings = material if hasattr(material, "displacement_method") else material.cycles
    settings.displacement_method = method


def emission_input_name(principled):
    name = "Emission Color" if "Emission Color" in principled.inputs else "Emission"
    return name
