# Autonomous Course + Reels Revenue Engine

Production-oriented system inspired by the uploaded video workflow: create a structured digital course/knowledge vault, generate short-form content, publish through official APIs, sell through a hosted checkout, and reconcile fulfillment and metrics.

## Scope

This repository intentionally does **not** promise revenue. The '$1500/month' claim shown in the source video is treated as an unverified marketing hypothesis. The system optimizes for measurable funnel outcomes, compliance, reproducibility, and fail-closed external actions.

## Core workflow

1. Research market/problem using approved web sources.
2. Build a Markdown knowledge vault/course graph.
3. Generate and QA lessons, landing-page copy, reels scripts, captions, thumbnails and CTAs.
4. Run policy, copyright, factuality and brand checks.
5. Require human approval for first-use credentials, new offers, legal claims, pricing changes, account-level changes and policy-sensitive actions.
6. Publish eligible reels through official Meta APIs only.
7. Route traffic to a checkout/payment link.
8. Receive signed payment webhooks and fulfill access idempotently.
9. Reconcile every external action and record evidence.
10. Run experiments and optimize conversion using bounded, auditable automation.

## Architecture

- `app/orchestrator.py`: deterministic state machine for autonomous workflow.
- `app/policy.py`: fail-closed policy engine and approval gates.
- `app/models.py`: durable intents and lifecycle states.
- `app/adapters/`: official external-service adapters only.
- `app/metrics.py`: funnel and revenue metrics; no fabricated projections.
- `config/policy.yaml`: autonomy, risk and compliance constraints.
- `docker-compose.yml`: PostgreSQL + application service.
- `tests/`: idempotency, approval and reconciliation tests.

## Autonomy boundary

The agent may autonomously research, draft, transform, schedule internal jobs, score content, run tests, compute metrics and prepare external actions. External writes are allowed only when the adapter is authenticated, the action is policy-allowed, the platform terms permit it, the action is idempotent/reconcilable, and any configured approval gate is satisfied.

Forbidden: CAPTCHA/anti-bot bypass, credential harvesting, identity/KYC automation, fake engagement, spam, deceptive claims, copyright infringement, unauthorized scraping, cookie/session theft, or bypassing platform limits.

## Recommended production integrations

- Claude Code/Agent SDK or another orchestrator for code/agent workflows.
- Obsidian-compatible Markdown vault as the portable course knowledge format.
- Meta Instagram Platform Content Publishing API for eligible Instagram publishing.
- Stripe Checkout/Payment Links + signed webhooks for payment and fulfillment.
- PostgreSQL as source of truth; Redis only for ephemeral locks/rate limits if added.
- OpenTelemetry for traces, metrics and logs.
- OpenBao/Vault-style workload identity for secrets in production.

## Revenue model

Do not hard-code '3 sales/day'. Treat it as a target. Track:

- qualified views
- profile/landing CTR
- landing conversion rate
- checkout-start rate
- paid conversion rate
- refunds/chargebacks
- CAC where paid distribution is used
- gross revenue
- fees
- refunds
- net settled revenue
- human hours

Primary business metric: `net_settled_revenue / human_hour`.

## Current status

This branch establishes the executable control-plane foundation. Production launch still requires real credentials, verified account eligibility, a real product/course, legal/tax review appropriate to the seller, end-to-end sandbox tests and explicit go-live approval.