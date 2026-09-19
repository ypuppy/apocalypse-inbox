"""Apply a realistic, image-based material pass to the existing house meshes.

This script deliberately does not generate, move, resize, or delete geometry.
Run it against the artist-edited source scene:

    & 'D:\Program Files\blender\blender.exe' --background assets/base-day-test.blend --python tools/render_house_material_pass.py
"""

from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "base-day-test.blend"
MODEL_REFINED_SOURCE = ROOT / "assets" / "base-day-model-refined.blend"
MATERIALS = ROOT / "assets" / "materials"


def load_image(nodes, path, label, non_color=False):
    image = bpy.data.images.load(str(path), check_existing=True)
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    node = nodes.new("ShaderNodeTexImage")
    node.name = label
    node.label = label
    node.image = image
    node.projection = "BOX"
    node.projection_blend = 0.35
    return node


def make_pbr(name, folder, slug):
    """Use the asset's base color, OpenGL normal, roughness and ARM maps directly."""
    files = {
        "diffuse": folder / f"{slug}_diff_2k.jpg",
        "normal": folder / f"{slug}_nor_gl_2k.jpg",
        "rough": folder / f"{slug}_rough_2k.jpg",
        "arm": folder / f"{slug}_arm_2k.jpg",
    }
    # The previously-downloaded door set is 4K; it remains distinct from walls/roof.
    if not files["diffuse"].exists() and slug == "rusty_metal_sheet":
        files = {key: folder / f"{slug}_{suffix}_4k.jpg" for key, suffix in {
            "diffuse": "diff", "normal": "nor_gl", "rough": "rough", "arm": "arm",
        }.items()}
    missing = [str(path) for path in files.values() if not path.exists()]
    if missing:
        raise RuntimeError("Required PBR maps are missing: " + ", ".join(missing))

    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    coordinates = nodes.new("ShaderNodeTexCoord")
    diffuse = load_image(nodes, files["diffuse"], "Base Color")
    normal = load_image(nodes, files["normal"], "Normal (OpenGL)", True)
    rough = load_image(nodes, files["rough"], "Roughness", True)
    arm = load_image(nodes, files["arm"], "Ambient / Roughness / Metallic", True)
    normal_map = nodes.new("ShaderNodeNormalMap")
    arm_channels = nodes.new("ShaderNodeSeparateColor")
    arm_channels.mode = "RGB"
    for texture in (diffuse, normal, rough, arm):
        links.new(coordinates.outputs["Generated"], texture.inputs["Vector"])
    links.new(arm.outputs["Color"], arm_channels.inputs["Color"])
    # Blender's physically based renderer already evaluates occlusion from the
    # geometry.  Feeding the packed AO channel into albedo double-darkens the
    # photo-scanned steel, so the source diffuse map is used unmodified.
    links.new(diffuse.outputs["Color"], shader.inputs["Base Color"])
    links.new(rough.outputs["Color"], shader.inputs["Roughness"])
    links.new(arm_channels.outputs["Blue"], shader.inputs["Metallic"])
    links.new(normal.outputs["Color"], normal_map.inputs["Color"])
    links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def make_window_glass():
    """A thin-window glass shader with CC0 photographed glass used as surface detail."""
    source = MATERIALS / "window_glass" / "window1.png"
    if not source.exists():
        raise RuntimeError(f"Missing CC0 window-glass texture: {source}")
    name = "Glass / CC0 photographed window surface"
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    coordinates = nodes.new("ShaderNodeTexCoord")
    glass_photo = load_image(nodes, source, "CC0 photographed glass texture")
    # The photograph supplies per-pixel glass/grime variation; transmission and
    # IOR make the thin panes respond as glass rather than a painted blue card.
    shader.inputs["Base Color"].default_value = (0.018, 0.055, 0.085, 1)
    shader.inputs["Metallic"].default_value = 0.05
    shader.inputs["Roughness"].default_value = 0.16
    if shader.inputs.get("Transmission Weight"):
        shader.inputs["Transmission Weight"].default_value = 0.72
    if shader.inputs.get("IOR"):
        shader.inputs["IOR"].default_value = 1.45
    links.new(coordinates.outputs["Generated"], glass_photo.inputs["Vector"])
    links.new(glass_photo.outputs["Color"], shader.inputs["Roughness"])
    links.new(shader.outputs["BSDF"], output.inputs["Surface"])
    return material


def assign(material, names):
    changed = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if not obj or not hasattr(obj.data, "materials"):
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        changed.append(name)
    return changed


def assign_prefix(material, prefixes):
    changed = []
    for obj in bpy.data.objects:
        if not hasattr(obj.data, "materials") or not any(obj.name.startswith(prefix) for prefix in prefixes):
            continue
        obj.data.materials.clear()
        obj.data.materials.append(material)
        changed.append(obj.name)
    return changed


def main():
    input_path = Path(bpy.data.filepath).resolve()
    if input_path not in {SOURCE.resolve(), MODEL_REFINED_SOURCE.resolve()}:
        raise RuntimeError(f"Open the artist-edited source or its model-refined derivative first: {SOURCE}")
    is_refined = input_path == MODEL_REFINED_SOURCE.resolve()
    output_blend = ROOT / "assets" / ("base-day-model-refined-materials.blend" if is_refined else "base-day-houses-test.blend")
    output_render = ROOT / "assets" / ("base-day-model-refined-materials.webp" if is_refined else "base-day-houses-test.webp")

    exterior = make_pbr("PBR / Poly Haven Metal Plate 02 — exterior", MATERIALS / "metal_plate_02", "metal_plate_02")
    roof = make_pbr("PBR / Poly Haven Worn Corrugated Iron — roof", MATERIALS / "worn_corrugated_iron", "worn_corrugated_iron")
    door = make_pbr("PBR / Poly Haven Rusty Metal Sheet — doors", MATERIALS / "rusty_metal_sheet", "rusty_metal_sheet")
    glass = make_window_glass()

    applied = {
        "exterior": assign(exterior, ["command center walls", "warehouse walls", "clinic walls"]),
        "roof": assign(roof, ["command center roof", "warehouse roof", "clinic roof"]),
        "door": assign(door, ["command center door", "warehouse door", "clinic door"]),
        "glass": assign(glass, [
            "command center window", "command center window.001",
            "warehouse window", "warehouse window.001",
            "clinic window", "clinic window.001",
        ]),
    }
    if is_refined:
        applied["exterior"] += assign_prefix(exterior, [
            "command facade", "command roof equipment", "command side HVAC",
            "warehouse facade", "warehouse cargo pallet", "warehouse safety bollard",
            "clinic facade", "clinic side generator", "clinic oxygen tank",
        ])
        applied["roof"] += assign_prefix(roof, [
            "command roof deck", "command front awning", "warehouse barrel roof",
            "warehouse roof rib", "warehouse cargo awning", "clinic roof cap", "clinic medical awning",
        ])
    if not is_refined:
        expected_counts = {"exterior": 3, "roof": 3, "door": 3, "glass": 6}
        if any(len(applied[kind]) != expected for kind, expected in expected_counts.items()):
            raise RuntimeError("House material assignment did not find every expected mesh: " + repr(applied))
    else:
        required_refined = {"command roof deck", "warehouse barrel roof", "clinic roof cap", "command front awning", "warehouse cargo awning"}
        assigned_refined = set(applied["exterior"] + applied["roof"])
        missing = required_refined - assigned_refined
        if missing:
            raise RuntimeError("Refined meshes were not assigned PBR materials: " + repr(sorted(missing)))

    scene = bpy.context.scene
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 95
    scene.render.filepath = str(output_render)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    bpy.ops.render.render(write_still=True)
    print("House materials applied:", applied)
    print("Saved derivative scene:", output_blend)
    print("Saved render:", output_render)


if __name__ == "__main__":
    main()
