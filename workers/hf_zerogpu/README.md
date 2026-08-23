# CineForge Hugging Face ZeroGPU smoke worker

Purpose: experimental smoke rendering only. This worker is not a production SLA backend.

## Quantitative constraints
- ZeroGPU large: 48 GB VRAM, 1x quota cost.
- ZeroGPU xlarge: 96 GB VRAM, 2x quota cost.
- Free account quota: approximately 5 GPU-minutes/day according to current official Hugging Face documentation.
- Gradio SDK only; queueing and runtime limits apply.

## Activation contract
1. The account/Space must be in good standing and ZeroGPU hosting must be available.
2. Pin model repository and revision/checkpoint; record license.
3. Record checkpoint SHA-256 or immutable Hub revision plus downloaded-artifact hashes.
4. Estimate smoke duration before allocation; do not start if the estimated GPU time exceeds remaining free quota.
5. Generate one original 3-5 second shot. No reference-source footage.
6. Export to a standard video file.
7. Run ffprobe/decode-integrity checks and CineForge visual QC.
8. Reject watermarked outputs.
9. Write `SmokeRenderEvidence` with prompt/checkpoint/output hashes.
10. Only after `eligible_to_enable=true` may the provider be enabled for further pilots.

## Model routing
For a 48 GB ZeroGPU allocation, CineForge may attempt the 24 GB-class path (Wan2.2 TI2V-5B) only if initialization + render fit inside the quota. If cold-start/model-loading dominates the free allocation, ZeroGPU should be treated as unsuitable for that checkpoint and the system must fail closed rather than repeatedly consuming quota.

## Security
- No browser automation to bypass queues or quotas.
- No token embedded in repository files.
- Use Hugging Face secrets/environment injection for credentials.
- Do not expose private prompts/assets through public Space logs.
