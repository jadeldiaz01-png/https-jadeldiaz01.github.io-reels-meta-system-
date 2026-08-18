from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SKILL_TESTS=sorted(Path("skills").glob("*/tests/test_skill.py"))
CASES=[]
for path in SKILL_TESTS:
    spec=importlib.util.spec_from_file_location(f"skill_test_{path.parents[1].name.replace('-','_')}",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    for name in sorted(dir(module)):
        if name.startswith("test_") and callable(getattr(module,name)):
            CASES.append((f"{path.parents[1].name}:{name}",getattr(module,name)))

@pytest.mark.parametrize("case",CASES,ids=[name for name,_ in CASES])
def test_executable_skill_behavior(case):
    _,fn=case
    fn()
