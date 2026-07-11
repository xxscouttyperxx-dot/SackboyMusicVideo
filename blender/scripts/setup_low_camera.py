import bpy
from mathutils import Vector
from common import ensure_collection

def point_at(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()

def build():
    col = ensure_collection("CAM_Rigs")
    data = bpy.data.cameras.get("CAM_Low_Data") or bpy.data.cameras.new("CAM_Low_Data")
    cam = bpy.data.objects.get("CAM_Low") or bpy.data.objects.new("CAM_Low", data)
    if not cam.users_collection:
        col.objects.link(cam)
    cam.location = (4.8,-6.5,0.28)
    cam.data.lens = 32
    point_at(cam, (0,0,1.65))
    print("Low camera built.")

if __name__ == "__main__":
    build()
