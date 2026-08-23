---
title: CineForge ZeroGPU Smoke Worker
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 5.49.1
app_file: app.py
pinned: false
license: apache-2.0
suggested_hardware: zerogpu
---

# CineForge ZeroGPU Smoke Worker

Experimental, fail-closed GPU worker for original 3–5 second CineForge smoke renders.

This Space is intentionally not a production SLA renderer. It requests Hugging Face ZeroGPU only inside the GPU-decorated render function, exposes a minimal Gradio API, pins the Wan2.2 TI2V-5B Diffusers model revision through `CINEFORGE_MODEL_REVISION`, and returns the generated MP4 plus machine-readable runtime metadata.

## Required Space configuration

1. Create a **Gradio** Space under a personal account eligible for ZeroGPU hosting.
2. Select **ZeroGPU / large (48 GB)** in Space hardware settings.
3. Copy this directory to the Space repository.
4. Set `CINEFORGE_MODEL_REVISION` to an immutable commit SHA from `Wan-AI/Wan2.2-TI2V-5B-Diffusers` before any governed smoke run.
5. If Hub authentication is needed, add `HF_TOKEN` as a Space secret; never commit it.
6. Keep the Space private if prompts/assets are sensitive and the account tier supports that configuration.

## Governance

- Original prompts only.
- No reference-source footage.
- No quota/queue bypass.
- A successful API response is **not** enough to enable the provider.
- CineForge must independently run decode/QC/watermark/provenance gates on the returned MP4.
- The provider remains disabled until `SmokeRenderEvidence.eligible_to_enable == true`.

The first pilot uses the existing `forest-light-rescue-001` concept and only one 3–5 second shot to conserve free quota.