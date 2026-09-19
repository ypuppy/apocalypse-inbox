"""Refine the three house meshes from the artist-edited base scene.

This is intentionally a derivative pass: it reads assets/base-day-test.blend
and writes assets/base-day-model-refined.blend.  The artist's source file is
never saved or overwritten.
"""

from pathlib import Path
import math

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "base-day-test.blend"
OUTPUT = ROOT / "assets" / "base-day-model-refined.blend"


def get_material(name):
    material = bpy.data.materials.get(name)
    if not material:
        raise RuntimeError(f"Expected source material not found: {name}")
    return material


METAL = None
SOLAR = None
CANVAS = None
CONCRETE = None


def cube(name, location, dimensions, material, bevel=0.0):
    hx, hy, hz = (value / 2 for value in dimensions)
    vertices = [(-hx, -hy, -hz), (hx, -hy, -hz), (hx, hy, -hz), (-hx, hy, -hz),
                (-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (4, 0, 3, 7)]
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    if bevel:
        modifier = obj.modifiers.new("edge radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def cylinder(name, location, radius, depth, material, vertices=12):
    mesh_vertices, faces = [], []
    for z in (-depth / 2, depth / 2):
        mesh_vertices.extend((radius * math.cos(math.tau * index / vertices), radius * math.sin(math.tau * index / vertices), z) for index in range(vertices))
    for index in range(vertices):
        next_index = (index + 1) % vertices
        faces.append((index, next_index, vertices + next_index, vertices + index))
    faces.extend((tuple(range(vertices)), tuple(range(vertices, vertices * 2))))
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(mesh_vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    return obj


def delete_object(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def barrel_roof(name, center, width, depth, wall_top, rise, material, segments=12):
    """A panelled hangar roof, more faithful to base-day's warehouse silhouette."""
    vertices, faces = [], []
    for side_x in (-width / 2, width / 2):
        for step in range(segments + 1):
            angle = math.pi * step / segments
            y = -depth / 2 + depth * step / segments
            z = wall_top + rise * math.sin(angle)
            vertices.append((side_x, y, z))
    for step in range(segments):
        faces.append((step, step + 1, segments + 2 + step, segments + 1 + step))
    # End caps make the roof a complete, readable volume.
    faces.append(tuple(range(segments + 1)))
    faces.append(tuple(range(segments + 1, (segments + 1) * 2)))
    mesh = bpy.data.meshes.new(name + " mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = center
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    return obj


def facade_frame(prefix, center, width, depth, height):
    """Visible structural frame so the metal plates are not a single plain block."""
    x, y = center
    front = y - depth / 2 - 0.026
    for offset in (-width / 2 + 0.13, width / 2 - 0.13):
        cube(f"{prefix} facade column", (x + offset, front, height / 2), (0.10, 0.05, height), METAL, 0.01)
    cube(f"{prefix} facade header", (x, front, height - 0.11), (width, 0.055, 0.10), METAL, 0.01)
    cube(f"{prefix} facade sill", (x, front, 0.20), (width, 0.055, 0.07), METAL, 0.01)


def entry_steps(prefix, x, front_y, width):
    cube(f"{prefix} entry lower step", (x, front_y - 0.18, 0.07), (width, 0.34, 0.14), CONCRETE, 0.025)
    cube(f"{prefix} entry upper step", (x, front_y - 0.07, 0.16), (width * 0.78, 0.22, 0.16), CONCRETE, 0.025)


def add_vent_bank(prefix, x, y, z, count=3):
    for index in range(count):
        vent = cube(f"{prefix} vent", (x + (index - (count - 1) / 2) * 0.19, y, z), (0.14, 0.055, 0.10), METAL, 0.01)
        vent.rotation_euler[0] = math.radians(14)


def refine_command():
    walls = bpy.data.objects["command center walls"]
    x, y, _ = walls.location
    width, depth, height = walls.dimensions
    front = y - depth / 2
    delete_object("command center roof")
    # Raised command deck, antenna/electronics enclosure, and a broad front awning.
    cube("command roof deck", (x, y, height + 0.06), (width + 0.30, depth + 0.26, 0.14), METAL, 0.035)
    cube("command roof equipment housing", (x + 0.18, y + 0.20, height + 0.25), (1.35, 0.76, 0.30), METAL, 0.03)
    cube("command front awning", (x, front - 0.18, height * 0.92), (1.12, 0.48, 0.08), METAL, 0.025)
    cube("command solar array", (x + 0.56, y + 0.42, height + 0.45), (0.88, 0.50, 0.06), SOLAR)
    bpy.context.object.rotation_euler[0] = math.radians(12)
    facade_frame("command", (x, y), width, depth, height)
    entry_steps("command", x, front, 0.82)
    add_vent_bank("command", x - 0.91, front - 0.05, height * 0.57)
    # Two side-mounted climate units signal a powered, modern command room.
    for side_x in (x - width / 2 - 0.11, x + width / 2 + 0.11):
        cube("command side HVAC", (side_x, y + 0.25, 0.43), (0.18, 0.44, 0.55), METAL, 0.02)


def refine_warehouse():
    walls = bpy.data.objects["warehouse walls"]
    x, y, _ = walls.location
    width, depth, height = walls.dimensions
    front = y - depth / 2
    delete_object("warehouse roof")
    barrel_roof("warehouse barrel roof", (x, y, 0), width + 0.30, depth + 0.28, height, 0.80, METAL)
    # Raised longitudinal ribs make the roof read as fabricated metal rather than a plain dome.
    for offset in (-1.16, -0.58, 0.0, 0.58, 1.16):
        rib = cube("warehouse roof rib", (x + offset, y, height + 0.64), (0.07, depth + 0.30, 0.055), METAL, 0.015)
    cube("warehouse cargo awning", (x, front - 0.22, height * 0.91), (1.60, 0.58, 0.11), METAL, 0.03)
    facade_frame("warehouse", (x, y), width, depth, height)
    entry_steps("warehouse", x, front, 1.28)
    # Loading dock: bollards, cargo pallet, and a recessed ventilation unit.
    for offset in (-1.08, 1.08):
        cylinder("warehouse safety bollard", (x + offset, front - 0.45, 0.28), 0.055, 0.56, METAL, 10)
    cube("warehouse cargo pallet", (x + 0.93, front - 0.62, 0.17), (0.48, 0.36, 0.34), METAL, 0.025)
    add_vent_bank("warehouse", x - 1.06, front - 0.05, height * 0.68, 4)


def refine_clinic():
    walls = bpy.data.objects["clinic walls"]
    x, y, _ = walls.location
    width, depth, height = walls.dimensions
    front = y - depth / 2
    # Keep the small clinic roof, but give it a raised steel cap and medical awning.
    cube("clinic roof cap", (x, y + 0.07, height + 0.34), (1.20, 0.78, 0.11), METAL, 0.025)
    cube("clinic medical awning", (x, front - 0.17, height * 0.87), (0.96, 0.48, 0.07), METAL, 0.025)
    facade_frame("clinic", (x, y), width, depth, height)
    entry_steps("clinic", x, front, 0.76)
    cube("clinic side generator", (x + width / 2 + 0.18, y + 0.22, 0.34), (0.26, 0.52, 0.50), METAL, 0.02)
    cylinder("clinic oxygen tank", (x - width / 2 - 0.15, y + 0.10, 0.38), 0.13, 0.76, METAL, 12)


def main():
    if Path(bpy.data.filepath).resolve() != SOURCE.resolve():
        raise RuntimeError(f"Open the artist-edited base scene first: {SOURCE}")
    global METAL, SOLAR, CANVAS, CONCRETE
    METAL = get_material("metal / oxidized")
    SOLAR = get_material("solar / blue black")
    CANVAS = get_material("canvas / tan")
    CONCRETE = get_material("concrete / dark")
    refine_command()
    refine_warehouse()
    refine_clinic()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
    print("Saved model-refined derivative:", OUTPUT)


if __name__ == "__main__":
    main()
