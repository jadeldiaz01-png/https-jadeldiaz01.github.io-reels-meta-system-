# CineForge Hardened Cinematic Pipeline

## Decision

CineForge is integrated as a governed cinematic orchestration layer, not as a monolithic renderer. PandaCineForge-style structured skills may inform planning and agent behavior, while rendering remains provider-agnostic and isolated behind adapters.

## Architecture

Trend Intelligence -> Concept Scoring -> Director -> Visual Bible -> Shot Planner -> Continuity Engine -> Image Quality Profile -> Policy/Budget Gate -> Model Router -> Render Workers -> Visual QC -> Audio Engine -> Deterministic Composer -> Delivery QC -> Human Approval -> Facebook Delivery -> Analytics Feedback.

## Core principles

1. Originality first. Trends and reference videos are research/quality signals, not source footage to copy.
2. Continuity and image-quality intent are planned before rendering.
3. Every shot is represented by a structured ShotContract.
4. Every generation attempt records provider, model, prompt hash, references, estimated/actual cost, latency and output hash.
5. No provider is a single point of failure. Fallback is allowed only if the quality floor is preserved.
6. Research acquisition must use allowlisted and policy-compliant sources. Anti-bot or Cloudflare bypass behavior is out of scope.
7. Publication remains human-approved by default.
8. Rendering is resumable and idempotent. Completed accepted shots are never regenerated solely because a later phase fails.
9. QC is fail-closed for policy, critical visual defects, continuity, image-quality floor and decode integrity.
10. Composition and master export are deterministic when possible, using Remotion/FFmpeg-class tooling rather than relying on a generative model for captions, stitching or final encoding.

## Loaded reference-video profile

The uploaded reference is treated only as a quality benchmark. Measured properties: 720x1280 vertical 9:16, 30 fps, HEVC, BT.709 primaries/transfer/space, AAC stereo at 44.1 kHz and approximately 4.32 Mbps video bitrate. Future delivery is upgraded to a minimum 1080x1920, H.264, AAC stereo 48 kHz and faststart while preserving useful perceptual properties rather than the original pixels.

The extracted perceptual signature includes natural available light, sunset highlight gradients, wet-surface specular reflections, foreground/midground/background depth, stable horizon, subject-background separation, natural motion cadence, restrained camera motion, environmental context and action progression understandable without text.

CineForge must never copy identities, watermarks/handles, exact third-party composition, exact action sequence or third-party audio from the reference.

## Image quality verification

`reference_quality_gate` evaluates 9:16 cadence and BT.709 delivery plus perceptual thresholds for highlight clipping, shadow crushing, flicker, jitter, motion-blur consistency, horizon stability, subject separation, layered depth, specular detail and compression artifacts. A failure blocks the asset from being called premium.

Thresholds are production controls, not claims that the uploaded reference itself was objectively measured for every perceptual metric. They encode the desired quality floor inferred from visual analysis and industry guidance.

## Model selection

`choose_render_capability` performs quality-first routing. It filters providers/models by reference consistency, image-to-video support, complex-motion control, camera control and premium-source capability. Historical visual-QC pass rate ranks eligible models; estimated cost only breaks quality ties and cannot override the required floor. If no model satisfies the shot requirements, routing fails closed instead of silently downgrading.

For reference-sensitive hero shots use models with persistent reference consistency and image-to-video. For complex physical action require motion control. For deliberate cinematography require camera control. Prefer 2K-or-higher source generation when it provides real detail, then finish to the target master. Simple inserts may use cheaper models only after satisfying the same acceptance criteria.

## Data model

Project -> Scene -> Shot -> GenerationAttempt -> Asset -> QCResult -> FinalMaster.

Artifacts should include provenance metadata and SHA-256 hashes. Storage adapters should support object stores such as Cloudflare R2 without coupling orchestration logic to a vendor.

## Cinematic contract

The Visual Bible locks palette, contrast, color temperature, lighting direction, atmosphere, focal language, depth of field and motion behavior.

Each shot locks subject, action, blocking, shot size, focal length, camera height/angle/movement, movement motivation, focus plan, lighting, exposure, white balance, physics constraints, continuity constraints, entry frame, exit frame and duration.

## Industry-grounded image intent

Image capture and finishing should protect dynamic range, color accuracy, detail rendition, signal-to-noise quality, natural motion characteristics and framing consistency. Frame-rate conversion should be avoided where possible because interpolation can introduce artifacts. Motion blur, judder, rolling-shutter-like skew and stabilization should be evaluated in context. Color finishing normalizes exposure/white-balance differences before applying a creative look.

These principles inform CineForge routing and QC; they do not impose Netflix acquisition requirements on Facebook delivery.

## Continuity gate

Before render, validate character identity, wardrobe, props, environment, weather, time-of-day, axis, eyeline, direction of travel, scale, exposure and color intent. A failed continuity plan blocks rendering.

## Quality gates

Technical: decode integrity, resolution, aspect ratio, FPS, codecs, audio sample rate, duration and timestamps.

Visual: black/frozen frames, morphing, anatomy, character drift, warping, flicker, jitter, ghosting, focus, exposure, physics, composition, highlight clipping, shadow crushing, motion-blur consistency, horizon stability, layered depth, subject separation, specular detail and compression artifacts.

Audio: clipping, missing sync cues, intelligibility, loudness consistency and spatial coherence.

Policy: originality, rights/permissions, platform rules, provenance and publication approval.

## Reliability

Use explicit job states, idempotency keys, bounded retries, UNKNOWN/reconciliation semantics for provider timeouts, provider circuit breakers, resumable ledgers and per-phase checkpoints. Do not restart an entire film when one shot fails.

## FinOps

Estimate cost before render, enforce a budget gate, track actual spend by shot and provider, and optimize quality-per-dollar using historical QC outcomes. Cost may break near-quality ties but must never override the quality floor. A fallback must not silently downgrade quality.

## Social feedback loop

After publication, ingest 1h/6h/24h/72h signals when available: watch time, retention, replays, shares, comments and qualified views. Feed these into concept scoring without allowing engagement metrics to bypass originality, safety or platform policy.
