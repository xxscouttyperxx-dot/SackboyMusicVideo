from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--video",required=True)
    parser.add_argument("--analysis",required=True)
    parser.add_argument("--raw",required=True)
    parser.add_argument("--processed",required=True)
    parser.add_argument("--overlay",required=True)
    parser.add_argument("--report",required=True)
    args=parser.parse_args()

    paths={
        "video":Path(args.video),
        "analysis":Path(args.analysis),
        "raw":Path(args.raw),
        "processed":Path(args.processed),
        "overlay":Path(args.overlay),
        "report":Path(args.report),
    }
    if not all(path.exists() for path in paths.values()):
        missing=[name for name,path in paths.items() if not path.exists()]
        print(f"POSE_CACHE_INVALID missing={missing}")
        return 2

    analysis=json.loads(paths["analysis"].read_text(encoding="utf-8"))
    raw=json.loads(paths["raw"].read_text(encoding="utf-8"))
    processed=json.loads(paths["processed"].read_text(encoding="utf-8"))

    source_hash=hashlib.sha256(paths["video"].read_bytes()).hexdigest()
    quality=processed.get("quality",{})
    checks={
        "source_hash":source_hash==analysis.get("sha256"),
        "raw_format":raw.get("format")=="SCOUTAI_MEDIAPIPE_POSE_RAW_V1",
        "processed_format":processed.get("format")=="SCOUTAI_MEDIAPIPE_POSE_PROCESSED_V1",
        "raw_source_hash":raw.get("metadata",{}).get("source_sha256")==source_hash,
        "processed_source_hash":processed.get("metadata",{}).get("source_sha256")==source_hash,
        "raw_frames":len(raw.get("frames",[]))==764,
        "processed_frames":len(processed.get("frames",[]))==764,
        "quality_passed":bool(quality.get("passed")),
        "detection_rate":float(quality.get("detection_rate",0.0))>=0.90,
        "overlay_nonempty":paths["overlay"].stat().st_size>100_000,
        "report_nonempty":paths["report"].stat().st_size>50,
    }
    if not all(checks.values()):
        print(f"POSE_CACHE_INVALID checks={checks}")
        return 3

    print("POSE_CACHE_OK")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
