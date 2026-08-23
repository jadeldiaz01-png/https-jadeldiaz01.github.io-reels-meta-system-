# CineForge Hardened Cinematic Pipeline

## Decision

CineForge is integrated as a governed cinematic orchestration layer, not as a monolithic renderer. PandaCineForge-style structured skills may inform planning and agent behavior, while rendering remains provider-agnostic and isolated behind adapters.

## Architecture

Trend Intelligence -> Concept Scoring -> Director -> Visual Bible -> Shot Planner -> Continuity Engine -> Policy/Budget Gate -> Model Router -> Render Workers -> Visual QC -> Audio Engine -> Deterministic Composer -> Delivery QC -> Human Approval -> Facebook Delivery -> Analytics Feedback.

## Core principles

1. Originality first. Trends are research signals, not source footage to copy.
2. Continuity is planned before rendering.
3. Every shot is represented by a structured ShotContract.
4. Every generation attempt records provider, model, prompt hash, references, estimated/actual cost, latency and output hash.
5. No provider is a single point of failure. Fallback is allowed only if the quality floor is preserved.
6. Research acquisition must use allowlisted and policy-compliant sources. Anti-bot or Cloudflare bypass behavior is out of scope.
7. Publication remains human-approved by default.
8. Rendering is resumable and idempotent. Completed accepted shots are never regenerated solely because a later phase fails.
9. QC is fail-closed for policy, critical visual defects, continuity and decode integrity.
10. Composition and master export are deterministic when possible, using Remotion/FFmpeg-class tooling rather than relying on a generative model for captions, stitching or final encoding.

## Data model

Project -> Scene -> Shot -> GenerationAttempt -> Asset -> QCResult -> FinalMaster.

Artifacts should include provenance metadata and SHA-256 hashes. Storage adapters should support object stores such as Cloudflare R2 without coupling orchestration logic to a vendor.

## Cinematic contract

The Visual Bible locks palette, contrast, color temperature, lighting direction, atmosphere, focal language, depth of field and motion behavior.

Each shot locks subject, action, blocking, shot size, focal length, camera height/angle/movement, movement motivation, focus plan, lighting, exposure, white balance, physics constraints, continuity constraints, entry frame, exit frame and duration.

## Model routing

Model selection is per-shot and health-aware. Route using capability, continuity requirements, motion complexity, reference support, latency, provider health, cost and historical QC pass rate. Hero shots and difficult physics can use premium models; simple inserts may use cheaper models only if the same QC floor is met.

## Continuity gate

Before render, validate character identity, wardrobe, props, environment, weather, time-of-day, axis, eyeline, direction of travel, scale, exposure and color intent. A failed continuity plan blocks rendering.

## Quality gates

Technical: decode integrity, resolution, aspect ratio, FPS, codecs, audio sample rate, duration and timestamps.

Visual: black/frozen frames, morphing, anatomy, character drift, warping, flicker, jitter, ghosting, focus, exposure, physics and composition.

Audio: clipping, missing sync cues, intelligibility, loudness consistency and spatial coherence.

Policy: originality, rights/permissions, platform rules, provenance and publication approval.

## Reliability

Use explicit job states, idempotency keys, bounded retries, UNKNOWN/reconciliation semantics for provider timeouts, provider circuit breakers, resumable ledgers and per-phase checkpoints. Do not restart an entire film when one shot fails.

## FinOps

Estimate cost before render, enforce a budget gate, track actual spend by shot and provider, and optimize quality-per-dollar using historical QC outcomes. A fallback must not silently downgrade quality.

## Social feedback loop

After publication, ingest 1h/6h/24h/72h signals when available: watch time, retention, replays, shares, comments and qualified views. Feed these into concept scoring without allowing engagement metrics to bypass originality, safety or platform policy.
