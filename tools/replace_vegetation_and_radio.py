"""Derive the user's refined base scene with imported CC0 vegetation and a rebuilt radio mast.

Input is intentionally read-only: assets/base-day-model-refined-lit.blend
Output is a separately named .blend and WebP render.
"""

import math
import os
import random

import bpy
from mathutils import Euler


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-model-refined-lit.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-vegetation-radio-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-vegetation-radio-test.webp")
GRASS_BLEND = os.path.join(
    ASSETS, "models", "polyhaven_grass_bermuda_01", "grass_bermuda_01_1k.blend"
)
KENNEY_FBX_ROOT = os.path.join(
    ASSETS, "models", "kenney_nature_kit", "source", "Models", "FBX format"
)


def require_file(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing required asset: " + path)


def remove_objects(predicate):
    for obj in list(bpy.data.objects):
        if predicate(obj):
            bpy.data.objects.remove(obj, do_unlink=True)


def active_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def link_copy(template, collection, name, location, rotation_z=0.0, scale=(1.0, 1.0, 1.0)):
    obj = template.copy()
    obj.name = name
    obj.location = location
    obj.rotation_euler = Euler((math.radians(90.0), 0.0, rotation_z), "XYZ")
    # FBX imports retain an authoring-unit conversion in object.scale. Preserve it
    # when placing copies; replacing it outright inflates Kenney meshes by 100x.
    obj.scale = (
        template.scale.x * scale[0],
        template.scale.y * scale[1],
        template.scale.z * scale[2],
    )
    collection.objects.link(obj)
    return obj


def append_grass_template():
    name = "grass_bermuda_01_geometry_nodes"
    with bpy.data.libraries.load(GRASS_BLEND, link=False) as (source, target):
        if name not in source.objects:
            raise RuntimeError("Poly Haven grass node object was not found")
        target.objects = [name]
    template = target.objects[0]
    if template is None:
        raise RuntimeError("Could not append Poly Haven grass")
    return template


def import_tree_template(filename):
    before = set(bpy.data.objects)
    bpy.ops.wm.fbx_import(filepath=os.path.join(KENNEY_FBX_ROOT, filename))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if not imported:
        raise RuntimeError("Could not import tree: " + filename)
    # Each Kenney FBX is a single mesh; leave its linked material data intact.
    return imported[0]


def make_smooth_cylinder(collection, name, radius, depth, location, material, rotation=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=32,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.materials.append(material)
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)
    return obj


def smooth_radio_material():
    original = bpy.data.materials.get("PBR / Poly Haven Metal Plate 02 — exterior")
    material = original.copy() if original else bpy.data.materials.new("PBR / smooth radio steel")
    material.name = "PBR / smooth radio steel — Metal Plate 02"
    material.use_nodes = True
    principled = next((n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if principled:
        if principled.inputs.get("Metallic"):
            principled.inputs["Metallic"].default_value = 0.96
        if principled.inputs.get("Roughness"):
            principled.inputs["Roughness"].default_value = 0.16
        if principled.inputs.get("Coat Weight"):
            principled.inputs["Coat Weight"].default_value = 0.28
        if principled.inputs.get("Coat Roughness"):
            principled.inputs["Coat Roughness"].default_value = 0.07
    return material


def brighten_window_glass():
    material = bpy.data.materials.get("Glass / CC0 photographed window surface")
    if material is None or not material.use_nodes:
        print("Window glass material not found; no window adjustment made")
        return
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    principled = next((node for node in nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled is None or principled.inputs.get("Base Color") is None:
        return

    base_color = principled.inputs["Base Color"]
    # Preserve the existing photographed-glass color source while mixing in a cool white.
    mixer = nodes.get("Window glass / cool white lift")
    if mixer is None:
        mixer = nodes.new("ShaderNodeMixRGB")
        mixer.name = "Window glass / cool white lift"
        mixer.label = "Cool white lift (keeps glass texture)"
    mixer.blend_type = "MIX"
    mixer.inputs[0].default_value = 0.22
    mixer.inputs[2].default_value = (0.58, 0.7, 0.78, 1.0)

    incoming = list(base_color.links)
    if incoming:
        source_socket = incoming[0].from_socket
        links.remove(incoming[0])
        links.new(source_socket, mixer.inputs[1])
    else:
        mixer.inputs[1].default_value = base_color.default_value
    links.new(mixer.outputs[0], base_color)
    if principled.inputs.get("Roughness"):
        principled.inputs["Roughness"].default_value = 0.2
    if principled.inputs.get("Transmission Weight"):
        principled.inputs["Transmission Weight"].default_value = 0.18
    if principled.inputs.get("Emission Color"):
        principled.inputs["Emission Color"].default_value = (0.1, 0.14, 0.18, 1.0)
    if principled.inputs.get("Emission Strength"):
        principled.inputs["Emission Strength"].default_value = 0.1


def set_principled_color(material, color, roughness=0.62):
    material.diffuse_color = (*color, 1.0)
    if not material.use_nodes:
        return
    principled = next((node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"), None)
    if principled:
        if principled.inputs.get("Base Color"):
            principled.inputs["Base Color"].default_value = (*color, 1.0)
        if principled.inputs.get("Roughness"):
            principled.inputs["Roughness"].default_value = roughness


def tune_imported_tree_materials():
    # Kenney's stock palette is bright cyan/pink. Retain its imported mesh forms,
    # but bring the palette into the dry, darker landscape of this base.
    for material in bpy.data.materials:
        lower = material.name.lower()
        if lower.startswith("leafsdark"):
            shade = (0.045, 0.2, 0.11) if not material.name.endswith(".001") else (0.075, 0.27, 0.13)
            set_principled_color(material, shade, 0.72)
        elif lower.startswith("woodbarkdark"):
            set_principled_color(material, (0.12, 0.043, 0.018), 0.82)
        elif material.name == "_defaultMat":
            set_principled_color(material, (0.055, 0.22, 0.12), 0.7)


def rebuild_left_radio_station():
    # Only the left ground station is replaced. The separate rooftop antenna remains untouched.
    old_station = [
        obj for obj in bpy.data.objects
        if obj.name.startswith("radio station") and obj.location.x < -4.0
    ]
    if old_station:
        center_x = sum(obj.location.x for obj in old_station) / len(old_station)
        center_y = sum(obj.location.y for obj in old_station) / len(old_station)
        # Object centers are symmetric; clamp to the known four-leg footprint center.
        center_x, center_y = -5.8, 2.138
    else:
        center_x, center_y = -5.8, 2.138
    remove_objects(lambda obj: obj.name.startswith("radio station") and obj.location.x < -4.0)

    collection = active_collection("Radio station / smooth metal pillars")
    metal = smooth_radio_material()
    base_z, pillar_height, radius = 0.08, 3.25, 0.43
    for index in range(12):
        angle = math.tau * index / 12.0
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        make_smooth_cylinder(
            collection,
            f"radio station smooth pillar {index + 1:02d}",
            0.035,
            pillar_height,
            (x, y, base_z + pillar_height / 2.0),
            metal,
        )
    # Three shallow collars visually bind the column array without reverting to a lattice tower.
    for index, z in enumerate((0.27, 1.68, 3.08), start=1):
        make_smooth_cylinder(
            collection,
            f"radio station metal collar {index}",
            0.5,
            0.065,
            (center_x, center_y, z),
            metal,
        )
    make_smooth_cylinder(
        collection,
        "radio station central receiver mast",
        0.045,
        1.28,
        (center_x, center_y, 3.84),
        metal,
    )
    # A small cross receiver makes the top read as an antenna from the top-down camera.
    make_smooth_cylinder(
        collection,
        "radio station receiver cross x",
        0.028,
        0.8,
        (center_x, center_y, 4.35),
        metal,
        rotation=(0.0, math.radians(90.0), 0.0),
    )
    make_smooth_cylinder(
        collection,
        "radio station receiver cross y",
        0.028,
        0.8,
        (center_x, center_y, 4.35),
        metal,
        rotation=(math.radians(90.0), 0.0, 0.0),
    )


def replace_vegetation():
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

    vegetation = active_collection("Vegetation / imported CC0 assets")
    broad_tree = import_tree_template("tree_detailed_dark.fbx")
    pine_tree = import_tree_template("tree_pineTallA_detailed.fbx")
    grass_template = append_grass_template()
    tune_imported_tree_materials()

    random.seed(2032)
    for index, (location, dimensions) in enumerate(tree_positions):
        # Keep the established interaction-area composition: exact old tree footprints,
        # with two linked imported CC0 tree variants for a less repetitive silhouette.
        if index % 4 == 0:
            template = pine_tree
            uniform = max(0.95, dimensions.x / 0.43)
        else:
            template = broad_tree
            uniform = max(0.84, dimensions.x / 0.88)
        uniform *= random.uniform(0.9, 1.08)
        link_copy(
            template,
            vegetation,
            f"CC0 tree {index + 1:02d}",
            (location.x, location.y, 0.055),
            rotation_z=random.uniform(0.0, math.tau),
            scale=(uniform, uniform, uniform),
        )

    # Use selected prior tuft locations, retaining the player's readable paths while
    # avoiding an overly expensive field of high-detail alpha-blended grass patches.
    for index, location in enumerate(grass_positions[::3]):
        scale = random.uniform(0.48, 0.68)
        tuft = grass_template.copy()
        tuft.name = f"CC0 Bermuda grass patch {index + 1:02d}"
        tuft.location = (location.x, location.y, 0.012)
        tuft.rotation_euler = (0.0, 0.0, random.uniform(0.0, math.tau))
        tuft.scale = (scale, scale, scale * random.uniform(0.85, 1.2))
        vegetation.objects.link(tuft)

    # Templates are only data sources; the visible scene contains linked copies.
    bpy.data.objects.remove(broad_tree, do_unlink=True)
    bpy.data.objects.remove(pine_tree, do_unlink=True)
    bpy.data.objects.remove(grass_template, do_unlink=True)


def main():
    require_file(SOURCE_BLEND)
    require_file(GRASS_BLEND)
    require_file(os.path.join(KENNEY_FBX_ROOT, "tree_detailed_dark.fbx"))
    require_file(os.path.join(KENNEY_FBX_ROOT, "tree_pineTallA_detailed.fbx"))
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("This script must run from base-day-model-refined-lit.blend")

    replace_vegetation()
    rebuild_left_radio_station()
    brighten_window_glass()

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
