# Skills Registry

Canonical entry point for reusable capabilities in the Autonomous Course + Reels Revenue Engine.

- `MASTER_SKILLS_2026.md` — governed master pack covering video engineering, agentic systems, infrastructure, continuous learning, software development, engineering, production operations and master orchestration.
- `_framework/` — manifest contract, validator and executable eval harness.
- `remotion-video/` — video composition/render planning with rights and QA boundaries.
- `agents-sdk-orchestrator/` — bounded agent/tool/handoff planning with approval-aware side effects.
- `devsecops-supply-chain/` — fail-closed release evidence gate for tests, scans, SBOM, provenance and signatures.
- `sre-production-readiness/` — SLO/observability/restore/reconciliation readiness gate.
- `research-evidence/` — auditable claim-to-source evidence matrix.
- `verified-skill-generator/` — autonomous DRAFT scaffold generation with traversal protection and no self-promotion.

## Executable contract

Every executable skill contains:

- `SKILL.md`
- `manifest.json`
- `scripts/`
- `schemas/`
- `tests/`
- `evals/`

Validate manifests and required layout:

```bash
python skills/_framework/validate_skill.py
```

Run behavioral eval cases:

```bash
python skills/_framework/run_evals.py
```

Run unit/contract tests:

```bash
pytest
```

## Integration rule

Skills define capability and procedure; they do not bypass `app/policy.py`, durable intent lifecycle, adapter authentication, approval gates or reconciliation. Generated skills start in `DRAFT`, cannot self-promote, and must pass review, tests/evals and production-readiness controls before production use.
