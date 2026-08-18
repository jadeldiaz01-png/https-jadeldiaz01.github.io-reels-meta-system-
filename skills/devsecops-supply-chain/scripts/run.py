from __future__ import annotations
import json, sys
from pathlib import Path
REQ=("tests","dependency_scan","secret_scan","sbom","provenance","signature")
def run(payload:dict)->dict:
    missing=[k for k in REQ if payload.get(k) is not True]
    return {"status":"NO_GO" if missing else "READY_FOR_RELEASE_APPROVAL","missing":missing,"approval_required":not missing,"external_write":False}
def main()->int:
    p=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else sys.stdin.read()); print(json.dumps(run(p),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
