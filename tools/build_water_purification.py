"""Add a PBR water-purification skid beside the clinic, derived from the user-edited farm scene."""

import math
import os

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-tree-grassland-farm-test.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-water-purification-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-water-purification-test.webp")
INDUSTRIAL_BLEND = os.path.join(
    ASSETS, "models", "oga_pbr_industrial_pack", "source", "OGA_industrial_a52_version", "industrial_final_cycles.blend"
)


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing asset: " + path)


def get_collection(name):
    value = bpy.data.collections.get(name)
    if value is None:
        value = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(value)
    return value


def move_to_collection(obj, target):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    target.objects.link(obj)


def cube(target, name, location, dimensions, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("equipment-pad bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    move_to_collection(obj, target)
    return obj


def cylinder(target, name, radius, depth, location, material, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    for polygon in obj.data.polygons:
        polygon.use_smooth = True
    obj.data.materials.append(material)
    move_to_collection(obj, target)
    return obj


def water_signal_material():
    material = bpy.data.materials.new("Water purifier / cyan status glass")
    material.use_nodes = True
    bsdf = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.015, 0.19, 0.24, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.1
        bsdf.inputs["Roughness"].default_value = 0.2
        if bsdf.inputs.get("Transmission Weight"):
            bsdf.inputs["Transmission Weight"].default_value = 0.35
        if bsdf.inputs.get("Emission Color"):
            bsdf.inputs["Emission Color"].default_value = (0.0, 0.22, 0.36, 1.0)
        if bsdf.inputs.get("Emission Strength"):
            bsdf.inputs["Emission Strength"].default_value = 1.4
    return material


def append_industrial_templates():
    wanted = ["tank_capsule_mat", "tank_sphere_mat", "tank_control_panel_mat", "pipe_04", "pipe_07"]
    with bpy.data.libraries.load(INDUSTRIAL_BLEND, link=False) as (source, target):
        missing = [name for name in wanted if name not in source.objects]
        if missing:
            raise RuntimeError("Industrial pack is missing: " + ", ".join(missing))
        target.objects = wanted
    return {obj.name: obj for obj in target.objects if obj is not None}


def place_copy(target, template, name, location, scale, rotation=(0.0, 0.0, 0.0)):
    obj = template.copy()
    obj.name = name
    obj.location = location
    obj.rotation_euler = rotation
    obj.scale = scale
    target.objects.link(obj)
    return obj


def build_purifier():
    # Clinic right edge is x=1.94; this two-metre skid begins at x=2.35,
    # outside its entrance-light clearance and within the existing fenced compound.
    target = get_collection("Water purification / PBR industrial skid")
    templates = append_industrial_templates()
    concrete = bpy.data.materials.get("concrete / dark")
    metal = bpy.data.materials.get("PBR / smooth radio steel — Metal Plate 02")
    if metal is None:
        metal = bpy.data.materials.get("PBR / Poly Haven Metal Plate 02 — exterior")
    signal = water_signal_material()
    center_x, center_y = 3.25, -2.08
    pad_z = 0.075
    cube(target, "water purification concrete service pad", (center_x, center_y, pad_z), (2.18, 1.75, 0.15), concrete, 0.04)

    # PBR imported equipment: sediment/carbon column, UV/pressure buffer and HMI terminal.
    main_tank = place_copy(target, templates["tank_capsule_mat"], "water purifier main filter column", (2.86, -2.02, 0.16), (0.155, 0.155, 0.155))
    buffer_tank = place_copy(target, templates["tank_sphere_mat"], "water purifier buffer pressure tank", (3.72, -1.9, 0.17), (0.155, 0.155, 0.155), (0.0, 0.0, math.radians(18)))
    panel = place_copy(target, templates["tank_control_panel_mat"], "water purifier control terminal", (3.86, -2.63, 0.16), (0.19, 0.19, 0.19), (0.0, 0.0, math.radians(180)))
    pipe_a = place_copy(target, templates["pipe_04"], "water purifier imported pipe loop", (3.32, -2.05, 0.28), (0.11, 0.11, 0.11), (0.0, 0.0, math.radians(90)))
    pipe_b = place_copy(target, templates["pipe_07"], "water purifier imported outlet pipe", (3.53, -2.25, 0.3), (0.15, 0.15, 0.15), (0.0, 0.0, math.radians(90)))

    # Directly visible water line and two cartridge housings make its function readable at game scale.
    cylinder(target, "water purifier supply pipe", 0.045, 0.88, (3.28, -2.08, 0.42), metal, (0.0, math.radians(90), 0.0))
    cylinder(target, "water purifier outlet pipe", 0.04, 0.72, (3.65, -2.23, 0.36), metal, (math.radians(90), 0.0, 0.0))
    for index, x in enumerate((3.05, 3.24), start=1):
        cylinder(target, f"water purifier transparent cartridge {index}", 0.09, 0.38, (x, -2.63, 0.36), signal)
        cylinder(target, f"water purifier cartridge cap {index}", 0.1, 0.035, (x, -2.63, 0.57), metal)
        cylinder(target, f"water purifier cartridge base {index}", 0.1, 0.035, (x, -2.63, 0.16), metal)
    cylinder(target, "water purifier illuminated flow gauge", 0.065, 0.045, (3.58, -2.58, 0.5), signal, (math.radians(90), 0.0, 0.0))

    # Low, focused task light: visible reflections without bleaching the clinic facade.
    bpy.ops.object.light_add(type="POINT", location=(3.3, -2.18, 1.6))
    light = bpy.context.object
    light.name = "water purifier cool inspection light"
    light.data.energy = 42.0
    light.data.color = (0.45, 0.75, 1.0)
    light.data.shadow_soft_size = 0.55
    move_to_collection(light, target)

    for template in templates.values():
        bpy.data.objects.remove(template, do_unlink=True)


def main():
    for path in (SOURCE_BLEND, INDUSTRIAL_BLEND):
        require(path)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from the user-edited farm blend only")
    build_purifier()
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.quality = 96
    scene.render.filepath = OUT_RENDER
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND)
    print("WROTE", OUT_BLEND)
    print("RENDERED", OUT_RENDER)


if __name__ == "__main__":
    main()
