# CineForge Free Video Runtime Strategy

## Objective

Enable at least one zero-per-render-cost video provider without lowering CineForge's existing quality, provenance, originality, rights, or publication gates.

## Provider classes

### FREE_LOCAL — eligible for automated production

1. **Wan2.2** — preferred free local provider. Apache-2.0 model license. Requires self-hosted GPU capacity and local model weights. Intended for text-to-video/image-to-video where the selected checkpoint supports the requested mode.
2. **LTX-Video classic** — secondary free local provider. Open-source code, local inference, image-to-video/text-to-video support; checkpoint/model license must be verified before activation. LTX-2.x is NOT implicitly covered by the classic Apache-2.0 assumption and must pass a separate license gate.
3. **HunyuanVideo 1.5** — optional local provider. Requires explicit territory/license gate because its community license excludes the EU, UK and South Korea. Never enable based only on technical availability.

All FREE_LOCAL providers default to `enabled=false`. A provider becomes enabled only after runtime provisioning verifies GPU, model hashes, license acceptance, dependency lock, disk capacity, successful smoke generation, QC and provenance capture.

### FREE_TRIAL — experimental only, not autonomous production

- Runway Free: one-time consumer credits; model availability is variable; free outputs can be watermarked; web-app credits are separate from API credits. Do not classify as a free API runtime.
- Luma Free: draft/personal-use constraints and watermark/plan limitations mean it is not a production provider.
- Hosted demos/Spaces: availability, queueing, rate limits and terms are not stable enough for an institutional runtime unless a specific endpoint is independently reviewed and approved.

### PAID_API

Runway API, Luma API, Google/Vertex video APIs and other paid inference endpoints remain optional provider adapters. Their presence must never prevent CineForge from using a validated FREE_LOCAL provider first when both meet the same QC floor.

## Provisioning gate for a FREE_LOCAL provider

A provider is enabled only if all are true:

- GPU/runtime capacity is detected and sufficient for the chosen quantization/checkpoint.
- Model source and SHA-256 are pinned.
- Code/dependency versions are locked.
- Model/code license passes policy for current geography and intended commercial use.
- No third-party watermark is introduced.
- The provider accepts structured CineForge shot contracts through an isolated adapter.
- A smoke render completes and decodes cleanly.
- The result passes image-quality, continuity and policy gates.
- Render attempt records seed when available, prompt hash, model id/version, checkpoint hash, duration, resolution, latency and output SHA-256.

## Routing policy

`FREE_LOCAL` is preferred only after quality and capability filtering. Cost never overrides the quality floor. If no zero-cost provider satisfies the shot contract, return `PROVIDER_UNAVAILABLE` or route to an explicitly approved paid provider. Never silently use consumer UI automation or watermark-bearing output for a commercial Facebook master.

## Current workspace evidence

The connected Runway workspace was authenticated successfully but reported no available video models. Therefore Runway is currently `PROVIDER_UNAVAILABLE` for video in this environment, independent of generic Free-plan marketing availability.

## Next infrastructure action

Provision one GPU-capable worker for Wan2.2, validate a pinned checkpoint, run a 3-5 second smoke render, record provenance and QC, and only then change the provider catalog entry from `enabled=false` to `enabled=true`.
