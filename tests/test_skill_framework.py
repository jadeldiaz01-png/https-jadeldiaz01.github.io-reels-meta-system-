from pathlib import Path

from skills._framework.validate_skill import validate


def test_all_executable_skills_satisfy_contract():
    root = Path("skills")
    manifests = list(root.glob("*/manifest.json"))
    assert manifests, "no executable skill manifests found"
    failures = {str(p.parent): validate(p.parent) for p in manifests}
    failures = {k: v for k, v in failures.items() if v}
    assert not failures, failures
