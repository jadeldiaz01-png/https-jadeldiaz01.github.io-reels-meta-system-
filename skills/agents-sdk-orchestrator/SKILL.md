---
name: agents-sdk-orchestrator
version: 1.0.0
domain: agentic
---
# Agents SDK Orchestrator

Design a minimal agent contract first, then expand only when specialist agents, handoffs, structured outputs or sandbox execution are justified by eval evidence.

## Workflow
1. Define goal, typed input/output, tools, state and approval boundaries.
2. Prefer one agent initially; add specialists only for measurable separation-of-concerns gains.
3. Treat deterministic actions as tools with explicit schemas.
4. Require approval for side effects and never expose secrets in prompts/evidence.
5. Emit an agent plan plus eval requirements; this skill does not call external APIs itself.

## Success
Produces a bounded orchestration plan with tool allowlist, approval classes, eval cases and no autonomous external writes.
