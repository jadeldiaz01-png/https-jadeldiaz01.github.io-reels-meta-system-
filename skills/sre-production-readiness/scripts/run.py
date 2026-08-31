from __future__ import annotations
import json, sys
from pathlib import Path
HARD=("restore_test","reconciliation")
REQ=("slo","observability","restore_test","runbook","capacity","reconciliation")
def run(payload:dict)->dict:
    hard=[k for k in HARD if payload.get(k) is not True]
    missing=[k for k in REQ if payload.get(k) is not True]
    status="NO_GO" if hard else ("CONDITIONAL_GO" if missing else "GO_CANDIDATE")
    return {"status":status,"missing":missing,"approval_required":status!="NO_GO","external_write":False}
def main()->int:
    p=json.loads(Path(sys.argv[1]).read_text() if len(sys.argv)>1 else sys.stdin.read()); print(json.dumps(run(p),indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
