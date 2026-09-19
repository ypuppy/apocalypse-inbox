"""Render a low-poly, pixel-style daytime base-map test with Blender.

This scene deliberately mirrors the Phaser interaction-zone composition in
app.js.  It only writes ``assets/base-day-test.webp``; the shipped
``assets/base-day.webp`` is never opened for writing.

Run from the repository root:
    & 'D:\Program Files\blender\blender.exe' --background --factory-startup --python tools/render_base_day_test.py
"""

from pathlib import Path
import math
import random

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "base-day-test.webp"
BLEND_OUTPUT = ROOT / "assets" / "base-day-test.blend"
TEXTURE_DIR = ROOT / "assets" / "materials" / "rusty_metal_sheet"
random.seed(22)

# Phaser's 1280 x 720 interaction coordinates, translated into the world.
# Keeping these anchors explicit makes future art passes safe for gameplay.
ZONE = {
    "command": (624, 233),
    "radio": (176, 189),
    "warehouse": (960, 229),
    "clinic": (713, 540),
    "relay": (190, 467),
    "gate": (625, 646),
    "garden": (327, 328),
    "water": (965, 513),
    "west-yard": (380, 487),
    "east-yard": (1120, 480),
}


def pos(name):
    """Map a Phaser zone center to the base's world-plane coordinates."""
    x, y = ZONE[name]
    return ((x - 640) / 80, (360 - y) / 80)


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def mat(name, color, roughness=0.9, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def enrich_material(material, shadow, highlight, noise_scale=5.0, roughness=0.65,
                    metallic=0.0, bump_strength=0.18):
    """Give an existing palette material a compact procedural PBR treatment.

    The maps are generated inside the .blend, so the delivered scene has no
    external texture-file dependency.
    """
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    texcoord = nodes.new("ShaderNodeTexCoord")
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 3.5
    noise.inputs["Roughness"].default_value = 0.72
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.28
    ramp.color_ramp.elements[0].color = (*shadow, 1)
    ramp.color_ramp.elements[1].position = 0.73
    ramp.color_ramp.elements[1].color = (*highlight, 1)
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.13
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    links.new(texcoord.outputs["Generated"], noise.inputs["Vector"])
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], shader.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])


def emission_material(name, color, strength):
    material = mat(name, color, 0.22, 0.0)
    shader = material.node_tree.nodes.get("Principled BSDF")
    emission_socket = shader.inputs.get("Emission Color") or shader.inputs.get("Emission")
    if emission_socket:
        emission_socket.default_value = (*color, 1)
    if shader.inputs.get("Emission Strength"):
        shader.inputs["Emission Strength"].default_value = strength
    return material


def image_texture(nodes, path, label, non_color=False):
    texture = nodes.new("ShaderNodeTexImage")
    texture.name = label
    texture.label = label
    texture.projection = "BOX"
    texture.projection_blend = 0.35
    texture.image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        texture.image.colorspace_settings.name = "Non-Color"
    return texture


def pbr_image_material(name, texture_dir):
    """Build a direct image-based PBR material from Poly Haven's CC0 maps.

    There is deliberately no procedural color/noise layer here: base color,
    ambient occlusion, roughness, metallic response and normal detail all
    come from the downloaded texture set.
    """
    required = {
        "diffuse": texture_dir / "rusty_metal_sheet_diff_4k.jpg",
        "normal": texture_dir / "rusty_metal_sheet_nor_gl_4k.jpg",
        "roughness": texture_dir / "rusty_metal_sheet_rough_4k.jpg",
        "arm": texture_dir / "rusty_metal_sheet_arm_4k.jpg",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise RuntimeError("Missing downloaded PBR texture maps: " + ", ".join(missing))
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    coords = nodes.new("ShaderNodeTexCoord")
    diffuse = image_texture(nodes, required["diffuse"], "Poly Haven / Diffuse")
    normal = image_texture(nodes, required["normal"], "Poly Haven / Normal GL", True)
    roughness = image_texture(nodes, required["roughness"], "Poly Haven / Roughness", True)
    arm = image_texture(nodes, required["arm"], "Poly Haven / ARM", True)
    normal_map = nodes.new("ShaderNodeNormalMap")
    normal_map.inputs["Strength"].default_value = 0.8
    separate_arm = nodes.new("ShaderNodeSeparateColor")
    separate_arm.mode = "RGB"
    multiply_ao = nodes.new("ShaderNodeMixRGB")
    multiply_ao.blend_type = "MULTIPLY"
    multiply_ao.inputs[0].default_value = 1.0
    for texture in (diffuse, normal, roughness, arm):
        links.new(coords.outputs["Generated"], texture.inputs["Vector"])
    links.new(diffuse.outputs["Color"], multiply_ao.inputs[1])
    links.new(arm.outputs["Color"], separate_arm.inputs["Color"])
    links.new(separate_arm.outputs["Red"], multiply_ao.inputs[2])
    links.new(multiply_ao.outputs["Color"], shader.inputs["Base Color"])
    links.new(roughness.outputs["Color"], shader.inputs["Roughness"])
    links.new(separate_arm.outputs["Blue"], shader.inputs["Metallic"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


M = {
    "grass": mat("terrain / olive grass", (0.19, 0.28, 0.09)),
    "grass_light": mat("terrain / sun grass", (0.35, 0.43, 0.13)),
    "dirt": mat("terrain / packed earth", (0.42, 0.25, 0.10)),
    "dirt_light": mat("terrain / dry dust", (0.59, 0.39, 0.16)),
    "wood": mat("wood / weathered", (0.22, 0.12, 0.055)),
    "wood_light": mat("wood / cut boards", (0.42, 0.24, 0.10)),
    "metal": mat("metal / oxidized", (0.19, 0.24, 0.19), 0.62, 0.35),
    "roof": mat("roof / green sheet", (0.16, 0.27, 0.18), 0.75, 0.15),
    "canvas": mat("canvas / tan", (0.58, 0.46, 0.25)),
    "medical": mat("medical / faded white", (0.72, 0.70, 0.52)),
    "red": mat("signal / red", (0.65, 0.07, 0.035)),
    "water": mat("water / tank blue", (0.12, 0.33, 0.35), 0.48, 0.3),
    "concrete": mat("concrete / dark", (0.25, 0.26, 0.20)),
    "leaf_dark": mat("foliage / deep", (0.07, 0.16, 0.045)),
    "leaf": mat("foliage / olive", (0.18, 0.32, 0.075)),
    "leaf_sun": mat("foliage / gold", (0.42, 0.42, 0.075)),
    "solar": mat("solar / blue black", (0.025, 0.07, 0.085), 0.3, 0.7),
}

enrich_material(M["grass"], (0.075, 0.12, 0.025), (0.29, 0.38, 0.075), 8.5, 0.88, 0.0, 0.28)
enrich_material(M["grass_light"], (0.17, 0.23, 0.04), (0.49, 0.52, 0.13), 10.0, 0.82, 0.0, 0.2)
enrich_material(M["dirt"], (0.16, 0.075, 0.025), (0.52, 0.29, 0.085), 6.5, 0.91, 0.0, 0.32)
enrich_material(M["dirt_light"], (0.28, 0.14, 0.045), (0.75, 0.48, 0.19), 8.0, 0.83, 0.0, 0.22)
enrich_material(M["wood"], (0.055, 0.022, 0.008), (0.35, 0.16, 0.045), 3.7, 0.61, 0.0, 0.36)
enrich_material(M["wood_light"], (0.16, 0.065, 0.018), (0.60, 0.32, 0.09), 4.2, 0.52, 0.0, 0.30)
enrich_material(M["metal"], (0.035, 0.055, 0.045), (0.31, 0.38, 0.30), 6.0, 0.38, 0.64, 0.18)
enrich_material(M["roof"], (0.025, 0.08, 0.04), (0.25, 0.42, 0.21), 5.5, 0.43, 0.35, 0.2)
enrich_material(M["canvas"], (0.20, 0.13, 0.055), (0.72, 0.59, 0.32), 11.0, 0.76, 0.0, 0.15)
enrich_material(M["medical"], (0.22, 0.22, 0.15), (0.87, 0.84, 0.62), 13.0, 0.62, 0.0, 0.08)
enrich_material(M["water"], (0.012, 0.08, 0.10), (0.13, 0.50, 0.54), 3.0, 0.18, 0.72, 0.1)
enrich_material(M["concrete"], (0.075, 0.08, 0.062), (0.39, 0.41, 0.32), 9.0, 0.74, 0.0, 0.24)
enrich_material(M["leaf_dark"], (0.012, 0.035, 0.006), (0.10, 0.24, 0.04), 4.0, 0.92, 0.0, 0.24)
enrich_material(M["leaf"], (0.03, 0.075, 0.012), (0.28, 0.48, 0.075), 5.0, 0.84, 0.0, 0.22)
enrich_material(M["leaf_sun"], (0.17, 0.10, 0.008), (0.68, 0.54, 0.07), 4.4, 0.73, 0.0, 0.18)
enrich_material(M["solar"], (0.003, 0.010, 0.015), (0.05, 0.19, 0.25), 3.0, 0.16, 0.9, 0.06)
M["window_glow"] = emission_material("interior / warm window glow", (1.0, 0.28, 0.035), 3.5)
M["lamp_glow"] = emission_material("lamp / sodium glow", (1.0, 0.56, 0.08), 8.0)
M["tech_glow"] = emission_material("technology / cyan status glow", (0.02, 0.63, 1.0), 6.0)
M["rusted_steel"] = pbr_image_material("PBR / Poly Haven Rusty Metal Sheet (CC0)", TEXTURE_DIR)


def cube(name, location, scale, material, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    if bevel:
        modifier = obj.modifiers.new("small bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 3
    return obj


def cylinder(name, location, radius, depth, material, vertices=8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    return obj


def gable_roof(name, location, width, depth, wall_top, rise, material):
    hx, hy = width / 2, depth / 2
    vertices = [
        (-hx, -hy, wall_top), (hx, -hy, wall_top), (hx, hy, wall_top), (-hx, hy, wall_top),
        (-hx, 0, wall_top + rise), (hx, 0, wall_top + rise),
    ]
    faces = [(0, 1, 5, 4), (3, 4, 5, 2), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    return obj


def add_building(name, xy, width, depth, wall_height, wall_mat=M["rusted_steel"], roof_mat=M["rusted_steel"]):
    x, y = xy
    cube(name + " walls", (x, y, wall_height / 2), (width / 2, depth / 2, wall_height / 2), wall_mat, 0.03)
    gable_roof(name + " roof", (x, y, 0), width + 0.14, depth + 0.14, wall_height, 0.46, roof_mat)
    # Door faces the bottom of the map, where the player enters each building.
    cube(name + " door", (x, y - depth / 2 - 0.008, 0.48), (0.22, 0.025, 0.46), M["rusted_steel"])
    for offset in (-width * 0.28, width * 0.28):
        cube(name + " window", (x + offset, y - depth / 2 - 0.012, wall_height * 0.63), (0.18, 0.02, 0.15), M["window_glow"])


def fence_segment(name, start, end):
    a, b = Vector((start[0], start[1], 0)), Vector((end[0], end[1], 0))
    vector = b - a
    length = vector.length
    midpoint = (a + b) / 2
    rail = cube(name + " rail", (midpoint.x, midpoint.y, 0.60), (length / 2, 0.035, 0.035), M["rusted_steel"])
    rail.rotation_euler[2] = math.atan2(vector.y, vector.x)
    rail = cube(name + " lower rail", (midpoint.x, midpoint.y, 0.27), (length / 2, 0.027, 0.027), M["rusted_steel"])
    rail.rotation_euler[2] = math.atan2(vector.y, vector.x)
    steps = max(2, round(length / 0.38))
    for index in range(steps + 1):
        point = a.lerp(b, index / steps)
        cylinder(name + " post", (point.x, point.y, 0.48), 0.045, 0.96, M["rusted_steel"], 8)


def tree(location, scale=1.0, autumn=False):
    x, y = location
    cylinder("tree trunk", (x, y, 0.35 * scale), 0.075 * scale, 0.7 * scale, M["wood"], 6)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.55 * scale, location=(x, y, 0.92 * scale))
    canopy = bpy.context.object
    canopy.name = "low-poly tree canopy"
    canopy.scale = (1.0, 0.82, 0.9)
    canopy.data.materials.append(M["leaf_sun"] if autumn else M["leaf"])
    subdivision = canopy.modifiers.new("Subdivision Surface", "SUBSURF")
    subdivision.levels = 1
    subdivision.render_levels = 1
    for polygon in canopy.data.polygons:
        polygon.use_smooth = True
    if random.random() > 0.55:
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.36 * scale, location=(x + 0.24 * scale, y - 0.1 * scale, 1.13 * scale))
        crown = bpy.context.object
        crown.data.materials.append(M["leaf_dark"])
        subdivision = crown.modifiers.new("Subdivision Surface", "SUBSURF")
        subdivision.levels = 1
        subdivision.render_levels = 1
        for polygon in crown.data.polygons:
            polygon.use_smooth = True


def crate(location, scale=1.0):
    x, y = location
    cube("supply crate", (x, y, 0.18 * scale), (0.19 * scale, 0.15 * scale, 0.18 * scale), M["rusted_steel"], 0.02)
    cube("crate strap", (x, y, 0.37 * scale), (0.205 * scale, 0.024 * scale, 0.02 * scale), M["solar"])


def grass_tuft(location, scale=1.0):
    x, y = location
    for index in range(3):
        blade = cube("angular grass", (x + index * 0.025, y + index * 0.018, 0.07 * scale), (0.014, 0.014, 0.08 * scale), M["grass_light"])
        blade.rotation_euler[1] = (-0.3 + index * 0.3)


def lamp(name, location, height=1.35):
    """A lit perimeter lamp: geometry and an actual warm point light."""
    x, y = location
    cylinder(name + " pole", (x, y, height / 2), 0.035, height, M["rusted_steel"], 8)
    cube(name + " housing", (x, y, height - 0.05), (0.10, 0.10, 0.07), M["rusted_steel"], 0.02)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=0.072, location=(x, y, height - 0.13))
    bulb = bpy.context.object
    bulb.name = name + " warm bulb"
    bulb.data.materials.append(M["lamp_glow"])
    bpy.ops.object.light_add(type="POINT", location=(x, y, height - 0.10))
    light = bpy.context.object
    light.name = name + " point light"
    light.data.energy = 38
    light.data.color = (1.0, 0.33, 0.055)
    light.data.shadow_soft_size = 0.32


def add_tower(name, xy, height=2.8, wide=0.62):
    x, y = xy
    # Four tapered legs and crossed braces make the radio / relay silhouettes legible.
    for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
        leg = cube(name + " tower leg", (x + dx * wide * 0.31, y + dy * wide * 0.31, height / 2), (0.035, 0.035, height / 2), M["rusted_steel"])
        leg.rotation_euler[1] = dy * 0.09
    for z in (0.65, 1.3, 1.95):
        brace_a = cube(name + " tower brace", (x, y, z), (wide * 0.47, 0.025, 0.025), M["rusted_steel"])
        brace_a.rotation_euler[2] = math.pi / 4
        brace_b = cube(name + " tower brace", (x, y, z + 0.08), (wide * 0.47, 0.025, 0.025), M["rusted_steel"])
        brace_b.rotation_euler[2] = -math.pi / 4
    cylinder(name + " antenna", (x, y, height + 0.32), 0.025, 0.72, M["rusted_steel"], 8)
    # Round dish, tilted toward the upper right of the screen.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=4, radius=0.30, location=(x + 0.08, y, height - 0.12))
    dish = bpy.context.object
    dish.name = name + " dish"
    dish.scale = (1, 0.18, 1)
    dish.rotation_euler[0] = math.radians(38)
    dish.data.materials.append(M["canvas"])


def patch_disc(name, location, radius, material, vertices=9, z=0.012):
    obj = cylinder(name, (location[0], location[1], z), radius, 0.02, material, vertices)
    obj.scale.y = random.uniform(0.58, 0.95)
    obj.rotation_euler[2] = random.random() * math.pi
    return obj


def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 92
    scene.render.filepath = str(OUTPUT)
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.3
    scene.view_settings.gamma = 1.0
    scene.render.use_file_extension = True

    scene.world.color = (0.055, 0.08, 0.028)
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.055, 0.08, 0.028, 1)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.42

    # Ground plane and faceted, patchy low-poly terrain.
    cube("base clearing", (0, 0, -0.08), (7.2, 5.2, 0.08), M["grass"])
    for _ in range(90):
        x, y = random.uniform(-6.75, 6.75), random.uniform(-4.55, 4.55)
        if (x / 7.0) ** 2 + (y / 4.75) ** 2 < 1:
            patch_disc("faceted grass", (x, y), random.uniform(0.08, 0.28), random.choice((M["grass"], M["grass_light"])), random.choice((5, 6, 7)))

    # A dirt cross connects all permanent stations and keeps the center open.
    cube("north south access road", (0.0, -0.55, 0.03), (0.72, 4.05, 0.035), M["dirt_light"], 0.12)
    cube("west east access road", (0.05, 0.05, 0.04), (5.55, 0.72, 0.04), M["dirt_light"], 0.10)
    patch_disc("central packed yard", (0.05, 0.0), 2.25, M["dirt"], 10, 0.045)
    for _ in range(34):
        x, y = random.uniform(-2.1, 2.1), random.uniform(-1.8, 1.8)
        patch_disc("yard dust", (x, y), random.uniform(0.05, 0.19), M["dirt_light"], random.choice((5, 6)), 0.06)

    # Palisade follows the original oval compound; leave the south-center opening for the gate.
    boundary = [(-5.7, -3.75), (-2.7, -4.45), (-1.1, -4.48), (1.1, -4.48), (2.8, -4.34), (5.9, -3.65), (6.95, -1.75), (7.0, 1.2), (5.65, 4.15), (2.9, 4.75), (0.0, 4.85), (-3.35, 4.6), (-5.95, 3.5), (-6.95, 1.2), (-6.85, -1.9), (-5.7, -3.75)]
    for index, (a, b) in enumerate(zip(boundary, boundary[1:])):
        # Keep the gate-facing stretch open.
        if index in (1, 2):
            continue
        fence_segment("perimeter %02d" % index, a, b)

    # Interaction anchors: radio upper-left, command center, warehouse upper-right,
    # clinic lower-center, relay lower-left, and the south gate.
    command = pos("command")
    add_building("command center", command, 3.0, 1.72, 1.16, M["rusted_steel"], M["rusted_steel"])
    cube("command solar awning", (command[0] + 0.66, command[1] + 0.58, 1.35), (0.58, 0.34, 0.035), M["solar"])
    bpy.context.object.rotation_euler[0] = math.radians(18)
    cylinder("command water barrel", (command[0] - 1.45, command[1] - 0.62, 0.22), 0.16, 0.43, M["water"], 8)
    cube("command status strip", (command[0], command[1] - 0.875, 1.05), (0.48, 0.015, 0.025), M["tech_glow"])
    lamp("command yard lamp", (command[0] - 1.9, command[1] - 0.60))

    warehouse = pos("warehouse")
    add_building("warehouse", warehouse, 3.1, 2.05, 1.45, M["rusted_steel"], M["rusted_steel"])
    cube("warehouse loading deck", (warehouse[0], warehouse[1] - 1.23, 0.17), (1.15, 0.35, 0.17), M["rusted_steel"])
    cube("warehouse access scanner", (warehouse[0] + 0.43, warehouse[1] - 1.05, 0.80), (0.055, 0.015, 0.10), M["tech_glow"])
    for offset in (-0.85, -0.5, 0.65, 1.00):
        crate((warehouse[0] + offset, warehouse[1] - 1.45), 0.85)
    lamp("warehouse loading lamp", (warehouse[0] + 1.60, warehouse[1] - 0.72))

    clinic = pos("clinic")
    add_building("clinic", clinic, 2.05, 1.45, 0.92, M["rusted_steel"], M["rusted_steel"])
    cube("clinic canopy", (clinic[0], clinic[1] - 0.95, 0.64), (0.56, 0.28, 0.04), M["rusted_steel"])
    cube("clinic cross vertical", (clinic[0], clinic[1] - 0.74, 1.25), (0.055, 0.025, 0.18), M["red"])
    cube("clinic cross horizontal", (clinic[0], clinic[1] - 0.76, 1.25), (0.18, 0.025, 0.055), M["red"])
    lamp("clinic entrance lamp", (clinic[0] + 1.13, clinic[1] - 0.62), 1.05)

    radio = pos("radio")
    add_tower("radio station", radio, 3.0, 0.78)
    cube("radio generator shed", (radio[0] + 0.7, radio[1] - 0.45, 0.35), (0.4, 0.35, 0.35), M["rusted_steel"])
    lamp("radio mast lamp", (radio[0] - 0.60, radio[1] - 0.5), 1.15)

    relay = pos("relay")
    add_tower("relay mast", relay, 2.15, 0.58)
    cube("relay equipment", (relay[0] + 0.52, relay[1] - 0.22, 0.26), (0.28, 0.25, 0.26), M["rusted_steel"])
    lamp("relay lamp", (relay[0] - 0.45, relay[1] - 0.3), 1.05)

    gate = pos("gate")
    fence_segment("south gate left", (-1.2, -4.43), (-0.8, -4.45))
    fence_segment("south gate right", (0.55, -4.45), (1.1, -4.46))
    for x in (-0.8, 0.55):
        cylinder("gate pillar", (x, -4.43, 0.75), 0.10, 1.5, M["rusted_steel"], 8)
    for x in (-0.42, 0.16):
        cube("gate door", (x, -4.46, 0.63), (0.26, 0.045, 0.62), M["rusted_steel"])
    cube("gate road", (gate[0], -4.74, 0.035), (0.75, 0.75, 0.035), M["dirt_light"])
    lamp("gate lamp left", (-0.98, -4.12), 1.45)
    lamp("gate lamp right", (0.75, -4.12), 1.45)

    # Reserved construction lots exactly where Phaser expects garden and water facilities.
    garden = pos("garden")
    patch_disc("garden soil plot", garden, 1.17, M["dirt"], 8, 0.07)
    for row in range(4):
        cube("garden raised bed", (garden[0] - 0.55 + row * 0.37, garden[1], 0.12), (0.10, 0.72, 0.10), M["rusted_steel"])
        for seed in range(4):
            grass_tuft((garden[0] - 0.55 + row * 0.37, garden[1] - 0.46 + seed * 0.28), 0.78)
    crate((garden[0] - 0.92, garden[1] - 0.6), 0.72)

    water = pos("water")
    patch_disc("water works pad", water, 1.12, M["concrete"], 8, 0.07)
    for dx, dy in ((-0.35, 0.14), (0.32, -0.12)):
        cylinder("water treatment tank", (water[0] + dx, water[1] + dy, 0.34), 0.31, 0.63, M["water"], 10)
        cylinder("tank cap", (water[0] + dx, water[1] + dy, 0.68), 0.12, 0.05, M["rusted_steel"], 8)
    cube("water pipes", (water[0], water[1], 0.35), (0.72, 0.06, 0.055), M["rusted_steel"])

    for yard_name in ("west-yard", "east-yard"):
        yard = pos(yard_name)
        patch_disc(yard_name + " staging soil", yard, 0.95, M["dirt"], 7, 0.065)
        crate((yard[0] - 0.26, yard[1] - 0.15), 0.9)
        crate((yard[0] + 0.22, yard[1] + 0.15), 0.72)
        for _ in range(5):
            grass_tuft((yard[0] + random.uniform(-0.65, 0.65), yard[1] + random.uniform(-0.65, 0.65)), 0.7)

    # Trees tightly frame the compound, leaving every Phaser zone unobstructed.
    for _ in range(52):
        angle = random.uniform(0, math.tau)
        radius = random.uniform(1.01, 1.22)
        x = math.cos(angle) * 7.15 * radius
        y = math.sin(angle) * 4.88 * radius
        tree((x, y), random.uniform(0.70, 1.22), autumn=random.random() > 0.67)
    for _ in range(42):
        x, y = random.uniform(-6.25, 6.25), random.uniform(-3.8, 3.8)
        # Avoid buildings and the central traversable yard.
        if (x / 2.55) ** 2 + (y / 2.1) ** 2 > 1.0 and random.random() > 0.38:
            grass_tuft((x, y), random.uniform(0.55, 1.15))

    # Lighting stays warm and graphic rather than photorealistic.
    bpy.ops.object.light_add(type="SUN", location=(-4, -5, 10))
    sun = bpy.context.object
    sun.name = "warm afternoon sun"
    sun.data.energy = 3.0
    sun.data.angle = math.radians(9)
    sun.data.color = (1.0, 0.74, 0.43)
    sun.rotation_euler = (math.radians(26), math.radians(-18), math.radians(-28))
    bpy.ops.object.light_add(type="AREA", location=(0, -1, 11))
    fill = bpy.context.object
    fill.name = "soft sky fill"
    fill.data.energy = 1050
    fill.data.shape = "DISK"
    fill.data.size = 10
    fill.data.color = (0.61, 0.78, 0.55)

    bpy.ops.object.camera_add(location=(0, -13.5, 15.8))
    camera = bpy.context.object
    camera.name = "isometric map camera"
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 15.2
    camera.data.lens = 50
    look_at(camera, (0, 0.0, 0))
    scene.camera = camera

    # Crisp facets and compact shadows read well after Phaser's integer scaling.
    scene.render.image_settings.color_mode = "RGB"
    scene.render.resolution_percentage = 100
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.use_file_extension = True
    scene.render.filepath = str(OUTPUT)
    # Keep the editable scene portable while retaining the original CC0 files
    # in assets/materials for future material swaps and attribution tracking.
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUTPUT))
    bpy.ops.render.render(write_still=True)
    print("Saved editable Blender scene to", BLEND_OUTPUT)
    print("Rendered test map to", OUTPUT)


if __name__ == "__main__":
    main()
