"""Add a CC0 outdoor HDRI lighting pass to the non-destructive house-material scene."""

from pathlib import Path
import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "base-day-houses-test.blend"
REFINED_SOURCE = ROOT / "assets" / "base-day-model-refined-materials.blend"
HDRI = ROOT / "assets" / "materials" / "qwantani_puresky" / "qwantani_puresky_2k.hdr"


def look_at(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main():
    input_path = Path(bpy.data.filepath).resolve()
    if input_path not in {SOURCE.resolve(), REFINED_SOURCE.resolve()}:
        raise RuntimeError(f"Open a material-pass scene first: {SOURCE}")
    is_refined = input_path == REFINED_SOURCE.resolve()
    output_blend = ROOT / "assets" / ("base-day-model-refined-lit.blend" if is_refined else "base-day-houses-lit-test.blend")
    output_render = ROOT / "assets" / ("base-day-model-refined-lit.webp" if is_refined else "base-day-houses-lit-test.webp")
    if not HDRI.exists():
        raise RuntimeError(f"Missing HDRI: {HDRI}")

    scene = bpy.context.scene
    scene.world.use_nodes = True
    nodes, links = scene.world.node_tree.nodes, scene.world.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputWorld")
    background = nodes.new("ShaderNodeBackground")
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.name = "Poly Haven Qwantani Pure Sky HDRI (CC0)"
    environment.image = bpy.data.images.load(str(HDRI), check_existing=True)
    background.inputs["Strength"].default_value = 0.45
    links.new(environment.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])

    # A broad, camera-side skylight exposes the dark metal panel faces without
    # changing any mesh, material map, camera, or artist placement.
    existing = bpy.data.objects.get("house facade sky fill")
    if existing:
        bpy.data.objects.remove(existing, do_unlink=True)
    light_data = bpy.data.lights.new("house facade sky fill", "AREA")
    fill = bpy.data.objects.new("house facade sky fill", light_data)
    bpy.context.collection.objects.link(fill)
    fill.location = (-0.2, -9.0, 7.5)
    light_data.energy = 1250
    light_data.shape = "DISK"
    light_data.size = 9.0
    light_data.color = (0.70, 0.84, 1.0)
    look_at(fill, (0, 0, 0.9))

    # Keep the artist's camera and meshes intact; only improve physical lighting
    # for metallic highlights and the glass panes' reflected sky.
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = 95
    scene.render.filepath = str(output_render)
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend))
    bpy.ops.render.render(write_still=True)
    print("Saved HDRI-lit derivative scene:", output_blend)
    print("Saved HDRI-lit render:", output_render)


if __name__ == "__main__":
    main()
