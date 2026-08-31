from __future__ import annotations
import json, sys
from pathlib import Path

ALLOWED_RIGHTS={"owned","licensed","public-domain","approved"}

def run(payload: dict) -> dict:
    required={"composition_id","width","height","fps","duration_frames","assets"}
    missing=sorted(required-payload.keys())
    if missing:
        raise ValueError(f"missing fields: {missing}")
    if payload["width"]<=0 or payload["height"]<=0 or payload["fps"]<=0 or payload["duration_frames"]<=0:
        raise ValueError("invalid render dimensions/timing")
    for asset in payload["assets"]:
        if not asset.get("source") or not asset.get("rights_status"):
            raise ValueError("asset provenance/rights required")
        if asset["rights_status"] not in ALLOWED_RIGHTS:
            raise ValueError("asset rights status not approved")
    return {"status":"READY_FOR_RENDER_QA","composition":payload["composition_id"],"render":{"width":payload["width"],"height":payload["height"],"fps":payload["fps"],"duration_frames":payload["duration_frames"]},"evidence":{"asset_count":len(payload["assets"]),"rights_checked":True},"external_write":False}

def main()->int:
    payload=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else sys.stdin.read())
    print(json.dumps(run(payload),indent=2)); return 0

if __name__=="__main__": raise SystemExit(main())
