from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = {"name","version","domain","risk","entrypoint","inputs","outputs","approvals","evidence","lifecycle"}
DOMAINS = {"video","agentic","devsecops","sre","research","skill-generation"}
LIFECYCLES = {"DRAFT","REVIEWED","TESTED","VALIDATED","PRODUCTION","DEPRECATED"}


def validate(skill_dir: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = skill_dir / "manifest.json"
    for required in ["SKILL.md", "manifest.json", "scripts", "schemas", "tests", "evals"]:
        if not (skill_dir / required).exists():
            errors.append(f"missing:{required}")
    if not manifest_path.exists():
        return errors
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    missing = REQUIRED - data.keys()
    errors += [f"manifest_missing:{k}" for k in sorted(missing)]
    if data.get("domain") not in DOMAINS:
        errors.append("invalid:domain")
    if data.get("lifecycle") not in LIFECYCLES:
        errors.append("invalid:lifecycle")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(data.get("version", ""))):
        errors.append("invalid:version")
    if data.get("self_promotion") is not False:
        errors.append("self_promotion_must_be_false")
    entry = data.get("entrypoint", "")
    if entry and not (skill_dir / entry).is_file():
        errors.append("entrypoint_not_found")
    if not data.get("evidence"):
        errors.append("evidence_required")
    return errors


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("skills")
    failures = {}
    for manifest in root.glob("*/manifest.json"):
        errs = validate(manifest.parent)
        if errs:
            failures[str(manifest.parent)] = errs
    print(json.dumps({"ok": not failures, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
