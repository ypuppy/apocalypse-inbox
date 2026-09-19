"""Add realistic, animated PBR puddles and iron accesswork to the latest edited base scene.

This pass deliberately opens the user-edited water-purifier blend read-only and saves
to a new file.  The ProcTexture CC0 map set is packed into the result.
"""

import math
import os
import random

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-water-purification-test.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-water-purification-wet-test.webp")
WATER_MAPS = os.path.join(
    ASSETS, "materials", "proctexture_water_surface", "source", "water-water-surface-1k"
)


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing required file: " + path)


def get_collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def link_only_to(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def image_node(nodes, path, label, non_color=False):
    image = bpy.data.images.get(os.path.basename(path))
    if image is None:
        image = bpy.data.images.load(path, check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    node = nodes.new("ShaderNodeTexImage")
    node.label = label
    node.name = label
    node.image = image
    return node


def make_water_material():
    old = bpy.data.materials.get("PBR / animated shallow water — ProcTexture Water Surface")
    if old:
        bpy.data.materials.remove(old, do_unlink=True)
    material = bpy.data.materials.new("PBR / animated shallow water — ProcTexture Water Surface")
    material.use_nodes = True
    try:
        material.surface_render_method = "DITHERED"
    except AttributeError:
        pass
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (980, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.name = "Physically reflective rainwater"
    bsdf.label = "Reflective rainwater / slight transparency"
    bsdf.location = (710, 0)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.075
    bsdf.inputs["IOR"].default_value = 1.333
    if bsdf.inputs.get("Transmission Weight"):
        bsdf.inputs["Transmission Weight"].default_value = 0.5
    if bsdf.inputs.get("Alpha"):
        bsdf.inputs["Alpha"].default_value = 0.93
    if bsdf.inputs.get("Coat Weight"):
        bsdf.inputs["Coat Weight"].default_value = 0.45
    if bsdf.inputs.get("Coat Roughness"):
        bsdf.inputs["Coat Roughness"].default_value = 0.025
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    texcoord = nodes.new("ShaderNodeTexCoord")
    texcoord.location = (-900, 0)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.name = "Water flow direction — animated"
    mapping.label = "Flow direction: animated eastward"
    mapping.location = (-720, 0)
    mapping.vector_type = "POINT"
    mapping.inputs["Scale"].default_value = (3.2, 8.5, 1.0)
    # A real keyframed offset lets the water flow when this blend is played or rendered as animation.
    mapping.inputs["Location"].default_value = (0.0, 0.0, 0.0)
    mapping.inputs["Location"].keyframe_insert("default_value", index=0, frame=1)
    mapping.inputs["Location"].default_value = (0.78, 0.17, 0.0)
    mapping.inputs["Location"].keyframe_insert("default_value", index=0, frame=120)
    links.new(texcoord.outputs["Generated"], mapping.inputs["Vector"])

    color = image_node(nodes, os.path.join(WATER_MAPS, "baseColor.png"), "CC0 water base color")
    color.location = (-470, 190)
    normal = image_node(nodes, os.path.join(WATER_MAPS, "normal.png"), "CC0 water normal", True)
    normal.location = (-470, -50)
    roughness = image_node(nodes, os.path.join(WATER_MAPS, "roughness.png"), "CC0 water roughness", True)
    roughness.location = (-470, -250)
    for texture in (color, normal, roughness):
        links.new(mapping.outputs["Vector"], texture.inputs["Vector"])

    # The PBR base is slightly tinted toward rainwater, while retaining its photographed ripple detail.
    tint = nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs["Fac"].default_value = 0.36
    tint.inputs[1].default_value = (0.025, 0.11, 0.13, 1.0)
    tint.location = (0, 190)
    links.new(color.outputs["Color"], tint.inputs[2])
    links.new(tint.outputs["Color"], bsdf.inputs["Base Color"])

    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.62
    normal_map.location = (5, -40)
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], bsdf.inputs["Normal"])
    roughness_math = nodes.new("ShaderNodeMath")
    roughness_math.operation = "MULTIPLY"
    roughness_math.inputs[1].default_value = 0.16
    roughness_math.location = (10, -245)
    links.new(roughness.outputs["Color"], roughness_math.inputs[0])
    links.new(roughness_math.outputs[0], bsdf.inputs["Roughness"])
    return material


def puddle_mesh(collection, name, center, radius_x, radius_y, material, seed, rotation=0.0):
    """Make a thin irregular puddle with one clean, horizontal reflective surface."""
    rng = random.Random(seed)
    vertices = []
    count = 18
    for i in range(count):
        angle = math.tau * i / count
        wobble = rng.uniform(0.82, 1.13)
        # More organic than an ellipse, but intentionally flat for believable shallow water.
        x = math.cos(angle) * radius_x * wobble
        y = math.sin(angle) * radius_y * wobble
        vertices.append((x, y, 0.0))
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], [tuple(range(count))])
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = center
    obj.rotation_euler[2] = rotation
    collection.objects.link(obj)
    return obj


def visible_size(obj):
    return max(abs(v) for v in obj.dimensions[:2])


def find_named(name):
    return bpy.data.objects.get(name)


def add_puddles(material):
    collection = get_collection("Weather / reflective rainwater")
    # The existing service pad is the positional anchor, so a user-moved purifier remains respected.
    pad = find_named("water purification concrete service pad")
    if pad:
        px, py = pad.location.x, pad.location.y
        top = pad.location.z + pad.dimensions.z / 2.0 + 0.004
        sx, sy = pad.dimensions.x, pad.dimensions.y
    else:
        px, py, top, sx, sy = 3.25, -2.08, 0.154, 2.18, 1.75
    puddle_mesh(collection, "purifier puddle / pooled runoff east", (px + sx * 0.31, py + sy * 0.25, top), 0.31, 0.17, material, 401, 0.28)
    puddle_mesh(collection, "purifier puddle / pooled runoff south", (px - sx * 0.19, py - sy * 0.37, top), 0.26, 0.12, material, 402, -0.42)
    puddle_mesh(collection, "purifier puddle / narrow drainage sheen", (px + sx * 0.07, py + sy * 0.43, top), 0.43, 0.075, material, 403, 0.08)

    # Use the user-edited farm bed itself as the anchor.  These shallow channels sit between crops.
    field = find_named("farm field / furrowed base")
    if not field:
        return
    fx, fy = field.location.x, field.location.y
    fz = field.location.z + field.dimensions.z / 2.0 + 0.022
    width, length = field.dimensions.x, field.dimensions.y
    # Four wet irrigation channels—just enough water to read as tended farmland, not a flooded plot.
    for index, fraction in enumerate((-0.30, -0.10, 0.10, 0.30), start=1):
        puddle_mesh(
            collection,
            f"farm irrigation water / channel {index}",
            (fx + width * fraction, fy + 0.015, fz),
            0.030,
            length * 0.39,
            material,
            460 + index,
            rng_rotation(index),
        )
    puddle_mesh(collection, "farm irrigation water / low-end pooled water", (fx - width * 0.26, fy - length * 0.40, fz), 0.28, 0.065, material, 477, -0.08)


def rng_rotation(index):
    return (-0.045, 0.025, -0.018, 0.038)[index - 1]


def iron_access_material():
    """Re-use the project's photographed rusty-metal PBR material rather than procedural metal."""
    material_name = "PBR / iron accesswork — oxidized sheet metal"
    old = bpy.data.materials.get(material_name)
    if old:
        bpy.data.materials.remove(old, do_unlink=True)
    candidates = [
        mat for mat in bpy.data.materials
        if "rusty metal sheet" in mat.name.lower() or "weathered steel" in mat.name.lower()
    ]
    if not candidates:
        candidates = [mat for mat in bpy.data.materials if "rust" in mat.name.lower() and mat.use_nodes]
    if not candidates:
        raise RuntimeError("The existing PBR rusty-metal material was not found in the edited scene")
    source = candidates[0]
    material = source.copy()
    material.name = material_name
    material.diffuse_color = (0.22, 0.095, 0.04, 1.0)
    return material, source.name


def render_iron_accesswork():
    material, source_name = iron_access_material()
    updated = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        name = obj.name.lower()
        if "door" not in name and "fence" not in name:
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        updated.append(obj.name)
    print("IRON_ACCESSWORK_SOURCE", source_name)
    print("IRON_ACCESSWORK_UPDATED", "; ".join(sorted(updated)))


def main():
    require(SOURCE_BLEND)
    for file_name in ("baseColor.png", "normal.png", "roughness.png"):
        require(os.path.join(WATER_MAPS, file_name))
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from the user-edited water-purifier blend only")
    water = make_water_material()
    add_puddles(water)
    render_iron_accesswork()
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = max(scene.frame_end, 120)
    scene.frame_set(1)
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
