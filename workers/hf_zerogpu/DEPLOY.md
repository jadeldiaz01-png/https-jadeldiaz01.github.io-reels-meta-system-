# CineForge ZeroGPU deployment gate

This deployment is intentionally fail-closed. A Space deployment does not enable Wan2.2 and does not make the E2E pilot `MASTER_READY` by itself.

## Required external credential

Create a Hugging Face user access token for the `Makubezxjadel` account with permission to create/update repositories and Spaces. Store it only as the GitHub Actions secret `HF_TOKEN`. Do not commit the token.

The ChatGPT Hugging Face OAuth connection currently has `jobs`, `openid`, `profile`, `read-mcp`, and `read-repos`; it does not have repository write scope, so it cannot create the Space directly.

## Deploy

Run GitHub Actions workflow `deploy-hf-zerogpu` with:

- `space_id=Makubezxjadel/cineforge-zerogpu`
- `model_revision=AUTO` (the workflow resolves `Wan-AI/Wan2.2-TI2V-5B-Diffusers` to its immutable Hub commit SHA and writes it as `CINEFORGE_MODEL_REVISION`)
- `private=true` for the first smoke test

The workflow creates/updates a Gradio Space using hardware flavor `zero-a10g`, uploads `workers/hf_zerogpu/space/`, sets `CINEFORGE_MODEL_ID` and `CINEFORGE_MODEL_REVISION`, and verifies that ZeroGPU was requested.

## Smoke evidence required

After the Space reaches RUNNING, invoke its `/smoke` Gradio endpoint through `cineforge.zerogpu_client`. The returned artifact remains `RENDERED_QC_PENDING` until all of the following are verified:

1. Observed CUDA GPU and at least 24 GB VRAM.
2. Exact model id and immutable model revision recorded.
3. Original prompt hash recorded.
4. Output MP4 SHA-256 recorded.
5. Duration between 3 and 5.5 seconds.
6. Decode integrity passes.
7. Visual QC passes.
8. No watermark is detected.
9. Policy gate passes.
10. `SmokeRenderEvidence.eligible_to_enable == true`.

Only after all gates pass may Wan2.2 change from `enabled=false` to `enabled=true`. The full pilot remains separate and still requires final 1080x1920 delivery QC before `MASTER_READY`.

## Cost policy

Do not substitute Hugging Face Jobs for ZeroGPU automatically. Jobs are pay-as-you-go and require a positive credit balance. Any paid GPU execution requires an explicit budget decision before launch.
