import bpy
from common import ensure_collection, move_to_collection, material, apply_material

COL = "ENV_ParkingLot"

def clear():
    col = bpy.data.collections.get(COL)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

def cube(name, loc, scale, mat, col):
    bpy.ops.mesh.primitive_cube_add(location=loc, scale=scale)
    obj = bpy.context.object
    obj.name = name
    apply_material(obj, mat)
    move_to_collection(obj, col)
    return obj

def build():
    clear()
    col = ensure_collection(COL)
    asphalt = material("MAT_Asphalt", (0.035,0.035,0.032,1), 0.93)
    wall = material("MAT_PlazaWall", (0.26,0.16,0.07,1), 0.78)
    glass = material("MAT_DarkGlass", (0.008,0.012,0.016,1), 0.22, 0.05)
    metal = material("MAT_BlackFrame", (0.006,0.006,0.008,1), 0.42, 0.55)

    cube("ENV_Asphalt", (0,0,-0.12), (18,18,0.10), asphalt, col)
    cube("ENV_PlazaShell", (0,8,2.4), (14,1.2,2.5), wall, col)

    for i in range(-3,4):
        x = i * 3.5
        cube(f"ENV_Glass_{i}", (x,6.72,2.25), (1.42,0.08,1.55), glass, col)
        cube(f"ENV_FrameL_{i}", (x-1.55,6.60,2.25), (0.055,0.08,1.65), metal, col)
        cube(f"ENV_FrameR_{i}", (x+1.55,6.60,2.25), (0.055,0.08,1.65), metal, col)
        cube(f"ENV_FrameTop_{i}", (x,6.60,3.90), (1.60,0.08,0.055), metal, col)

    print("Parking lot graybox built.")

if __name__ == "__main__":
    build()
