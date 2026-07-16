
import bpy, sys

SCRIPT_VERSION="1.2"
RIG="SACKBOY_RIG_PLACEMENT_V1"
COLLECTIONS=["CTRL_Main","CTRL_IK","CTRL_Poles","DEF_Skeleton"]

args=sys.argv
mode=None
if "--" in args:
    extra=args[args.index("--")+1:]
    for index,value in enumerate(extra):
        if value=="--mode" and index+1<len(extra):
            mode=extra[index+1]

if mode not in {"controls","full"}:
    raise RuntimeError("Expected --mode controls or --mode full")

arm=bpy.data.objects.get(RIG)
if arm is None or arm.type!="ARMATURE":
    raise RuntimeError(f"Missing armature {RIG}")

for name in COLLECTIONS:
    if arm.data.collections.get(name) is None:
        raise RuntimeError(f"Missing bone collection {name}")

arm.data.collections["CTRL_Main"].is_visible=True
arm.data.collections["CTRL_IK"].is_visible=True
arm.data.collections["CTRL_Poles"].is_visible=True
arm.data.collections["DEF_Skeleton"].is_visible=(mode=="full")
arm["Rig_View_Default"]="FULL_SKELETON" if mode=="full" else "CONTROLS_ONLY"

bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print(f"[rig_view_mode] version={SCRIPT_VERSION} mode={mode} deform_visible={arm.data.collections['DEF_Skeleton'].is_visible}")
