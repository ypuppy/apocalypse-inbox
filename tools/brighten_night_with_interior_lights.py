"""Add practical exterior lamps and emissive interior windows to the derived night scene."""

import os

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-night.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-night-lit.blend")
OUT_RENDER = os.path.join(ASSETS, "base-night-phaser-lit.webp")


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing source blend: " + path)


def collection(name):
    value = bpy.data.collections.get(name)
    if value is None:
        value = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(value)
    return value


def emissive_glass(name, color, strength):
    material = bpy.data.materials.get(name)
    if material:
        bpy.data.materials.remove(material, do_unlink=True)
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    bsdf = next(node for node in nodes if node.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.22
    bsdf.inputs["Metallic"].default_value = 0.0
    if bsdf.inputs.get("Transmission Weight"):
        bsdf.inputs["Transmission Weight"].default_value = 0.08
    if bsdf.inputs.get("Emission Color"):
        bsdf.inputs["Emission Color"].default_value = color
    if bsdf.inputs.get("Emission Strength"):
        bsdf.inputs["Emission Strength"].default_value = strength
    return material


def assign(obj, material):
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(material)


def add_practical_light(target, name, location, color, energy, radius=0.055):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=radius, location=location)
    bulb = bpy.context.object
    bulb.name = name + " / visible bulb"
    bulb.data.materials.append(emissive_glass(name + " / bulb emission", color, 8.0))
    target.objects.link(bulb)
    for old in list(bulb.users_collection):
        if old != target:
            old.objects.unlink(bulb)
    bpy.ops.object.light_add(type="POINT", location=location)
    light = bpy.context.object
    light.name = name + " / point light"
    light.data.energy = energy
    light.data.color = color[:3]
    light.data.shadow_soft_size = 0.62
    target.objects.link(light)
    for old in list(light.users_collection):
        if old != target:
            old.objects.unlink(light)


def add_night_lighting():
    target = collection("Night lighting / practical fixtures")
    warm = (1.0, 0.30, 0.055, 1.0)
    sodium = (1.0, 0.48, 0.11, 1.0)
    cool = (0.17, 0.68, 1.0, 1.0)

    # Each fixture is a visible bulb plus a real local light; locations preserve the game-scale clear paths.
    fixtures = [
        ("garden grow-lamp", (-3.67, 2.24, 1.08), sodium, 105),
        ("clinic path-lamp", (1.52, -3.10, 1.05), warm, 125),
        ("water service-lamp", (3.00, -1.25, 1.22), cool, 145),
        ("east perimeter guard-lamp", (5.72, -1.64, 1.22), warm, 100),
        ("west perimeter guard-lamp", (-5.90, -0.62, 1.18), warm, 95),
    ]
    for fixture in fixtures:
        add_practical_light(target, *fixture)

    # Window emission supplies the interior read without point-light leakage through the low-poly roofs.
    warm_window = emissive_glass("Night / warm emissive glass", (1.0, 0.24, 0.055, 1.0), 2.15)
    cool_window = emissive_glass("Night / cool emissive glass", (0.22, 0.68, 1.0, 1.0), 1.55)
    for obj in bpy.data.objects:
        if obj.type != "MESH" or "window" not in obj.name.lower():
            continue
        assign(obj, cool_window if "command" in obj.name.lower() else warm_window)

    # A small increase avoids complete silhouette loss while remaining clearly darker than day.
    for obj in bpy.data.objects:
        if obj.type == "LIGHT" and "fill" in obj.name.lower():
            obj.data.energy = 28.0


def main():
    require(SOURCE_BLEND)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from the current Blender night scene only")
    add_night_lighting()
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 96
    scene.render.filepath = OUT_RENDER
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("WROTE", OUT_BLEND)
    print("RENDERED", OUT_RENDER)


if __name__ == "__main__":
    main()
