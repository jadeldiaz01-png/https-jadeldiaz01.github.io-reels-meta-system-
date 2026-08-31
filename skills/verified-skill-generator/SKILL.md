---
name: verified-skill-generator
version: 1.0.0
domain: skill-generation
---
# Verified Skill Generator

Generate a complete draft executable skill scaffold from a bounded specification.

The generator creates `SKILL.md`, `manifest.json`, `scripts/run.py`, `schemas/input.schema.json`, `tests/test_skill.py` and `evals/cases.json`. Generated skills always start at `DRAFT`, set `self_promotion=false`, and cannot declare production readiness, privileged external writes or approval bypasses.

The default mode is dry-run. `--apply` may write only below an explicitly supplied skills root, after validating the generated name and preventing path traversal. Promotion remains a separate reviewed/tested production-readiness process.
