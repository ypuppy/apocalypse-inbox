"""Derive a dedicated night background from the user-positioned Blender camera."""

import os

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-test.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-night.blend")
OUT_RENDER = os.path.join(ASSETS, "base-night-phaser.webp")


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing source blend: " + path)


def set_emissive_strength(material, strength):
    if not material or not material.use_nodes:
        return
    for node in material.node_tree.nodes:
        if node.type != "BSDF_PRINCIPLED":
            continue
        if node.inputs.get("Emission Strength"):
            node.inputs["Emission Strength"].default_value = strength


def make_night():
    scene = bpy.context.scene
    # Preserve a faint blue moonlit read on the terrain; daylight fills are nearly removed.
    for obj in bpy.data.objects:
        if obj.type != "LIGHT":
            continue
        name = obj.name.lower()
        if "sun" in name:
            obj.data.energy = 0.055
            obj.data.color = (0.18, 0.31, 0.72)
        elif "fill" in name:
            obj.data.energy = 16.0
            obj.data.color = (0.13, 0.22, 0.45)
        elif "water purifier" in name:
            obj.data.energy = 210.0
            obj.data.color = (0.32, 0.74, 1.0)
            obj.data.shadow_soft_size = 0.7
        else:
            # The existing practical lamps carry the night scene, casting local warm pools of light.
            obj.data.energy = 190.0
            obj.data.color = (1.0, 0.27, 0.045)
            obj.data.shadow_soft_size = 0.5

    if scene.world and scene.world.use_nodes:
        for node in scene.world.node_tree.nodes:
            if node.type == "BACKGROUND":
                node.inputs["Color"].default_value = (0.002, 0.007, 0.025, 1.0)
                node.inputs["Strength"].default_value = 0.08
    for material in bpy.data.materials:
        lowered = material.name.lower()
        if "lamp" in lowered or "glow" in lowered or "status" in lowered:
            set_emissive_strength(material, 5.0 if "water" not in lowered else 7.0)

    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 96
    scene.render.filepath = OUT_RENDER
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("WROTE", OUT_BLEND)
    print("RENDERED", OUT_RENDER)


def main():
    require(SOURCE_BLEND)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from the user-adjusted perimeter blend only")
    make_night()


if __name__ == "__main__":
    main()
