"""Render-ready tree and full grassland pass derived from the user's refined source scene."""

import math
import os
import random
import sys

import bpy

sys.path.insert(0, os.path.dirname(__file__))
import replace_vegetation_and_radio as previous_pass


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-model-refined-lit.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-tree-grassland-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-tree-grassland-test.webp")
TREE_BLEND = os.path.join(ASSETS, "models", "opengameart_toon_tree", "treetoonstylized01.blend")
GRASSLAND_BLEND = os.path.join(ASSETS, "materials", "withered_grass", "withered_grass_1k.blend")


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing asset: " + path)


def remove_objects(predicate):
    for obj in list(bpy.data.objects):
        if predicate(obj):
            bpy.data.objects.remove(obj, do_unlink=True)


def append_tree_template():
    target_name = "TreeToonStylizedStyle01(Optimized)"
    with bpy.data.libraries.load(TREE_BLEND, link=False) as (source, target):
        if target_name not in source.objects:
            raise RuntimeError("Optimized render tree is absent from the source blend")
        target.objects = [target_name]
        target.images = [
            name for name in source.images
            if name in {"TextureUVTreeToonStylizedStyle01.png", "TreeToonStylizedStyle01_UV_N.png"}
        ]
    return target.objects[0]


def modernize_tree_material(tree_template):
    """Convert the source's packed Blender-Internal texture maps to Principled BSDF."""
    material = tree_template.material_slots[0].material
    diffuse = bpy.data.images.get("TextureUVTreeToonStylizedStyle01.png")
    normal = bpy.data.images.get("TreeToonStylizedStyle01_UV_N.png")
    if material is None or diffuse is None:
        raise RuntimeError("Packed toon-tree diffuse texture was not appended")
    material.name = "PBR / rendered toon tree — packed diffuse + normal"
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (620, 0)
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.location = (360, 0)
    principled.inputs["Roughness"].default_value = 0.67
    texture = nodes.new("ShaderNodeTexImage")
    texture.name = "Packed tree diffuse atlas"
    texture.image = diffuse
    texture.location = (-280, 30)
    links.new(texture.outputs["Color"], principled.inputs["Base Color"])
    if texture.outputs.get("Alpha") and principled.inputs.get("Alpha"):
        links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
    if normal is not None:
        normal.colorspace_settings.name = "Non-Color"
        normal_texture = nodes.new("ShaderNodeTexImage")
        normal_texture.name = "Packed tree normal atlas"
        normal_texture.image = normal
        normal_texture.location = (-280, -190)
        normal_map = nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = 0.45
        normal_map.location = (80, -160)
        links.new(normal_texture.outputs["Color"], normal_map.inputs["Color"])
        links.new(normal_map.outputs["Normal"], principled.inputs["Normal"])
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    try:
        material.surface_render_method = "DITHERED"
    except AttributeError:
        pass


def append_grassland_material():
    with bpy.data.libraries.load(GRASSLAND_BLEND, link=False) as (source, target):
        if "withered_grass" not in source.materials:
            raise RuntimeError("Withered grass material is absent from the source blend")
        target.materials = ["withered_grass"]
    material = target.materials[0]
    material.name = "PBR / Poly Haven Withered Grass — base clearing"
    mapping = material.node_tree.nodes.get("Mapping") if material.use_nodes else None
    if mapping and mapping.inputs.get("Scale"):
        # The source scan is 2 m wide; repeat it across the 14.4 x 10.4 m clearing.
        mapping.inputs["Scale"].default_value = (7.2, 5.2, 1.0)
    # Preserve the scan's detail, but shift its dry tan toward an inhabited,
    # slightly stressed grassland rather than a sand-colored clearing.
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    diffuse = nodes.get("Image Texture")
    if principled and diffuse and principled.inputs.get("Base Color"):
        base = principled.inputs["Base Color"]
        for link in list(base.links):
            links.remove(link)
        tint = nodes.new("ShaderNodeMixRGB")
        tint.name = "Grassland / survival green tint"
        tint.label = "Keeps scan detail; adds muted grass green"
        tint.blend_type = "MIX"
        tint.inputs[0].default_value = 0.7
        tint.inputs[2].default_value = (0.045, 0.16, 0.025, 1.0)
        tint.location = (principled.location.x - 240, principled.location.y + 120)
        links.new(diffuse.outputs["Color"], tint.inputs[1])
        links.new(tint.outputs[0], base)
    return material


def replace_trees_and_grass_tufts():
    tree_positions = [
        (obj.location.copy(), obj.dimensions.copy())
        for obj in bpy.data.objects
        if obj.name.startswith("low-poly tree canopy")
    ]
    grass_positions = [
        obj.location.copy()
        for obj in bpy.data.objects
        if obj.name.startswith("faceted grass")
    ]
    remove_objects(lambda obj: obj.name.startswith("angular grass"))
    remove_objects(lambda obj: obj.name.startswith("faceted grass"))
    remove_objects(lambda obj: obj.name.startswith("low-poly tree canopy"))
    remove_objects(lambda obj: obj.name.startswith("tree trunk"))

    collection = previous_pass.active_collection("Vegetation / render-ready imported assets")
    tree_template = append_tree_template()
    modernize_tree_material(tree_template)
    grass_template = previous_pass.append_grass_template()
    random.seed(2032)
    for index, (location, dimensions) in enumerate(tree_positions):
        tree = tree_template.copy()
        tree.name = f"render-ready toon tree {index + 1:02d}"
        # Original rendered model is 8.8 m across; match each replaced tree's prior
        # canopy footprint so Phaser's interaction composition remains readable.
        target_width = max(dimensions.x, dimensions.y)
        scale = (target_width / 8.8) * random.uniform(0.88, 1.08)
        tree.location = (location.x, location.y, 0.012)
        tree.rotation_euler = (0.0, 0.0, random.uniform(0.0, math.tau))
        tree.scale = (scale, scale, scale)
        collection.objects.link(tree)

    # PBR Bermuda clumps remain as close foreground detail over the grassland scan.
    for index, location in enumerate(grass_positions[::3]):
        tuft = grass_template.copy()
        tuft.name = f"PBR Bermuda grass detail {index + 1:02d}"
        tuft.location = (location.x, location.y, 0.013)
        tuft.rotation_euler = (0.0, 0.0, random.uniform(0.0, math.tau))
        scale = random.uniform(0.44, 0.62)
        tuft.scale = (scale, scale, scale * random.uniform(0.85, 1.15))
        collection.objects.link(tuft)

    bpy.data.objects.remove(tree_template, do_unlink=True)
    bpy.data.objects.remove(grass_template, do_unlink=True)


def apply_grassland():
    clearing = bpy.data.objects.get("base clearing")
    if clearing is None or clearing.type != "MESH":
        raise RuntimeError("Could not find base clearing mesh")
    material = append_grassland_material()
    clearing.data.materials.clear()
    clearing.data.materials.append(material)


def main():
    for path in (SOURCE_BLEND, TREE_BLEND, GRASSLAND_BLEND, previous_pass.GRASS_BLEND):
        require(path)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from base-day-model-refined-lit.blend only")
    replace_trees_and_grass_tufts()
    apply_grassland()
    previous_pass.rebuild_left_radio_station()
    previous_pass.brighten_window_glass()
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
