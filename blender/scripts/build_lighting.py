import bpy
from common import ensure_collection

COL = "LGT_Night"

def clear():
    col = bpy.data.collections.get(COL)
    if col:
        for obj in list(col.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

def add_area(name, loc, energy, size, color):
    col = ensure_collection(COL)
    ld = bpy.data.lights.new(name=name, type='AREA')
    ld.energy = energy
    ld.shape = 'DISK'
    ld.size = size
    ld.color = color
    obj = bpy.data.objects.new(name, ld)
    obj.location = loc
    col.objects.link(obj)
    return obj

def build():
    clear()
    bpy.context.scene.world.color = (0.002,0.002,0.004)
    for idx, x in enumerate((-9,-3,3,9)):
        add_area(f"LGT_Amber_{idx}", (x,1.0,7.0), 1100.0, 4.5, (1.0,0.38,0.08))
    fill = add_area("LGT_PlazaFill", (0,5.0,4.0), 650.0, 10.0, (1.0,0.25,0.04))
    fill.rotation_euler = (1.5708,0,0)
    print("Night lighting built.")

if __name__ == "__main__":
    build()
