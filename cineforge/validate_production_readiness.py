import json
from pathlib import Path

data=json.loads(Path('cineforge/production_readiness.json').read_text(encoding='utf-8'))
gates=data.get('gates') or {}
blockers=data.get('blockers') or []
decision=data.get('decision')
if data.get('schema_version') != '1.0.0':
    raise SystemExit('MEDIA_READINESS=FAIL schema')
if decision not in {'BLOCKED','CONDITIONAL','PRODUCTION_READY'}:
    raise SystemExit('MEDIA_READINESS=FAIL decision')
if not gates or any(type(v) is not bool for v in gates.values()):
    raise SystemExit('MEDIA_READINESS=FAIL gates')
if decision == 'PRODUCTION_READY' and (blockers or not all(gates.values())):
    raise SystemExit('MEDIA_READINESS=FAIL unsafe promotion')
if decision != 'PRODUCTION_READY' and not blockers:
    raise SystemExit('MEDIA_READINESS=FAIL missing blockers')
print(f"MEDIA_READINESS=PASS decision={decision} gates={sum(gates.values())}/{len(gates)}")
