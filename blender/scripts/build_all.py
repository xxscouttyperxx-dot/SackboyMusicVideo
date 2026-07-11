import sys
from pathlib import Path
p = Path(__file__).resolve().parent
if str(p) not in sys.path:
    sys.path.insert(0, str(p))

from common import save_project, purge_startup_scene_objects
import build_character, build_parking_lot, build_lighting
import setup_camera_orbit, setup_low_camera

print("=== BUILD START ===")
purge_startup_scene_objects()
build_character.build()
build_parking_lot.build()
build_lighting.build()
setup_camera_orbit.build()
setup_low_camera.build()
save_project()
print("=== BUILD COMPLETE ===")
