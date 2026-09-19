"""Add a fenced, furrowed farm plot to the user-edited grassland scene without overwriting it."""

import os

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-tree-grassland-test.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-tree-grassland-farm-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-tree-grassland-farm-test.webp")
FARM_MATERIAL_BLEND = os.path.join(ASSETS, "materials", "farm_furrows", "farm_furrows_1k.blend")
FENCE_OBJ = os.path.join(
    ASSETS, "models", "opengameart_steel_fence", "source", "Fence Steel-Concrete", "fence-steel-concrete-steel.obj"
)


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing asset: " + path)


def collection(name):
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def move_to_collection(obj, target):
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
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
        modifier = obj.modifiers.new("soft packed-earth edge", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    move_to_collection(obj, target)
    return obj


def append_farm_material():
    with bpy.data.libraries.load(FARM_MATERIAL_BLEND, link=False) as (source, target):
        if "farm_furrows" not in source.materials:
            raise RuntimeError("Farm Furrows material was not found")
        target.materials = ["farm_furrows"]
    material = target.materials[0]
    material.name = "PBR / Poly Haven Farm Furrows — raised beds"
    if material.use_nodes:
        mapping = material.node_tree.nodes.get("Mapping")
        if mapping and mapping.inputs.get("Scale"):
            # The source scan is 2.1 m tall: preserve one readable furrow run per bed.
            mapping.inputs["Scale"].default_value = (1.0, 1.0, 1.0)
    return material


def farm_fence_material():
    material = bpy.data.materials.new("PBR / farm fence weathered steel")
    material.name = "PBR / farm fence weathered steel"
    material.use_nodes = True
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled:
        if principled.inputs.get("Metallic"):
            principled.inputs["Metallic"].default_value = 0.92
        if principled.inputs.get("Roughness"):
            principled.inputs["Roughness"].default_value = 0.27
        if principled.inputs.get("Base Color"):
            principled.inputs["Base Color"].default_value = (0.055, 0.14, 0.13, 1.0)
    return material


def crop_material():
    material = bpy.data.materials.new("Farm crop / young leaves")
    material.use_nodes = True
    bsdf = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.025, 0.17, 0.035, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.72
    return material


def make_crop_cluster(target, index, x, y, z, material):
    # Three small, crossed leaves form one newly planted crop cluster.
    for leaf, angle in enumerate((0.0, 2.094, 4.188), start=1):
        bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.024, radius2=0.006, depth=0.18, location=(x, y, z + 0.09))
        obj = bpy.context.object
        obj.name = f"farm crop {index:02d} leaf {leaf}"
        obj.rotation_euler = (0.42, 0.0, angle)
        obj.data.materials.append(material)
        move_to_collection(obj, target)


def import_fence_template():
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=FENCE_OBJ)
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError("Could not import modular steel fence")
    return imported[0]


def add_fence_segment(target, template, material, name, location, length_scale=1.0, rotate=False):
    obj = template.copy()
    obj.name = name
    # Source module: thin X axis, 2 m length on Y, 2 m height on Z.
    obj.scale = (1.0, length_scale, 0.42)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, 1.57079632679 if rotate else 0.0)
    obj.data.materials.clear()
    obj.data.materials.append(material)
    target.objects.link(obj)
    return obj


def build_plot():
    plot = bpy.data.objects.get("garden soil plot")
    if plot is None:
        raise RuntimeError("The reserved garden soil plot was not found")
    target = collection("Farm plot / left of command house")
    furrows = append_farm_material()
    fence_metal = farm_fence_material()
    crops = crop_material()
    center_x, center_y = plot.location.x, plot.location.y
    bed_width, bed_height = 2.06, 1.78
    base_z = plot.location.z + 0.035

    # Retain the editable reserved plot below, and build a gently raised farm slab on it.
    base = cube(target, "farm field / furrowed base", (center_x, center_y, base_z), (bed_width, bed_height, 0.07), furrows, 0.025)
    # The physical bed rows catch light separately from the PBR scan's own furrows.
    row_count = 7
    row_width = 0.205
    for row in range(row_count):
        x = center_x - 0.78 + row * 0.26
        cube(
            target,
            f"farm field / raised furrow {row + 1}",
            (x, center_y, base_z + 0.06),
            (row_width, 1.54, 0.055),
            furrows,
            0.018,
        )
        for seed in range(4):
            y = center_y - 0.55 + seed * 0.36
            make_crop_cluster(target, row * 4 + seed + 1, x, y, base_z + 0.09, crops)

    # Imported CC0 modular fence encloses the beds. A small south opening reads as a gate.
    template = import_fence_template()
    x_half, y_half = 1.14, 0.99
    fence_z = base_z + 0.34
    add_fence_segment(target, template, fence_metal, "farm fence / west", (center_x - x_half, center_y, fence_z), 1.0)
    add_fence_segment(target, template, fence_metal, "farm fence / east", (center_x + x_half, center_y, fence_z), 1.0)
    add_fence_segment(target, template, fence_metal, "farm fence / north", (center_x, center_y + y_half, fence_z), 1.08, True)
    add_fence_segment(target, template, fence_metal, "farm fence / south gate left", (center_x - 0.66, center_y - y_half, fence_z), 0.42, True)
    add_fence_segment(target, template, fence_metal, "farm fence / south gate right", (center_x + 0.66, center_y - y_half, fence_z), 0.42, True)
    bpy.data.objects.remove(template, do_unlink=True)


def main():
    for path in (SOURCE_BLEND, FARM_MATERIAL_BLEND, FENCE_OBJ):
        require(path)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this script from the user-edited base-day-tree-grassland-test.blend")
    build_plot()
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
