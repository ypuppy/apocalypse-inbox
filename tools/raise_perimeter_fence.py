"""Raise and metal-finish the outer perimeter fence without altering the edited source blend."""

import os

import bpy


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
SOURCE_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-test.blend")
OUT_BLEND = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-test.blend")
OUT_RENDER = os.path.join(ASSETS, "base-day-water-purification-wet-perimeter-test.webp")


def require(path):
    if not os.path.isfile(path):
        raise RuntimeError("Missing source blend: " + path)


def material_for_perimeter():
    name = "PBR / perimeter fence — oxidized iron"
    existing = bpy.data.materials.get(name)
    if existing:
        bpy.data.materials.remove(existing, do_unlink=True)
    source = bpy.data.materials.get("PBR / iron accesswork — oxidized sheet metal")
    if source is None:
        raise RuntimeError("Missing the previously packed iron PBR material")
    result = source.copy()
    result.name = name
    return result


def assign_material(obj, material):
    # Avoid changing a mesh datablock that could be shared with a user object outside the fence.
    if obj.data.users > 1:
        obj.data = obj.data.copy()
    obj.data.materials.clear()
    obj.data.materials.append(material)


def is_outer_fence(obj):
    name = obj.name.lower()
    return name.startswith("perimeter ") or name.startswith("south gate ")


def duplicate_middle_rail(obj, material):
    middle = obj.copy()
    middle.data = obj.data.copy()
    middle.name = obj.name.replace(" rail", " middle rail")
    middle.location.z = 0.74
    assign_material(middle, material)
    for collection in obj.users_collection:
        collection.objects.link(middle)
    return middle


def raise_perimeter():
    iron = material_for_perimeter()
    posts = rails = middle_rails = 0
    for obj in list(bpy.data.objects):
        if obj.type != "MESH" or not is_outer_fence(obj):
            continue
        name = obj.name.lower()
        assign_material(obj, iron)
        if " post" in name:
            # Retain the existing ground contact, raise the top from 0.96m to 1.42m.
            bottom = obj.location.z - obj.dimensions.z / 2.0
            obj.dimensions.z = 1.42
            obj.location.z = bottom + obj.dimensions.z / 2.0
            posts += 1
        elif "lower rail" in name:
            # Lower rail stays near ground; upper rails establish the new security-fence height.
            obj.location.z = 0.31
            rails += 1
        elif name.endswith(" rail"):
            obj.location.z = 1.17
            duplicate_middle_rail(obj, iron)
            rails += 1
            middle_rails += 1
    print("RAISED_PERIMETER_POSTS", posts)
    print("REPOSITIONED_PERIMETER_RAILS", rails)
    print("ADDED_PERIMETER_MIDDLE_RAILS", middle_rails)


def main():
    require(SOURCE_BLEND)
    if os.path.normcase(os.path.abspath(bpy.data.filepath)) != os.path.normcase(SOURCE_BLEND):
        raise RuntimeError("Run this pass from the latest user-edited wet blend only")
    raise_perimeter()
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
