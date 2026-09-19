import bpy

for material in bpy.data.materials:
    print("MAT", material.name)

for prefix in ("radio station", "tree trunk", "low-poly tree canopy", "angular grass", "faceted grass"):
    objects = [obj for obj in bpy.data.objects if obj.name.startswith(prefix)]
    print("GROUP", prefix, len(objects))
    for obj in objects[:12]:
        print("OBJ", obj.name, tuple(round(v, 3) for v in obj.location), tuple(round(v, 3) for v in obj.dimensions), [slot.material.name if slot.material else None for slot in obj.material_slots])

for obj in bpy.data.objects:
    names = [slot.material.name if slot.material else "" for slot in obj.material_slots]
    if any(name.startswith("terrain /") for name in names):
        print("TERRAIN", obj.name, tuple(round(v, 3) for v in obj.location), tuple(round(v, 3) for v in obj.dimensions), names)
    if obj.type == "MESH" and max(obj.dimensions.x, obj.dimensions.y) > 5:
        print("LARGE", obj.name, tuple(round(v, 3) for v in obj.dimensions), names)
    if any(term in obj.name.lower() for term in ("clinic", "medical", "medic")):
        print("MEDICAL", obj.name, tuple(round(v, 3) for v in obj.location), tuple(round(v, 3) for v in obj.dimensions), names)
    if any(term in obj.name.lower() for term in ("water", "tank", "barrel")):
        print("WATER", obj.name, tuple(round(v, 3) for v in obj.location), tuple(round(v, 3) for v in obj.dimensions), names)
    if any(term in obj.name.lower() for term in ("door", "fence")):
        print("ACCESS", obj.name, tuple(round(v, 3) for v in obj.location), tuple(round(v, 3) for v in obj.dimensions), names)
