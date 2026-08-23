from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import time

import gradio as gr
import spaces
import torch
from diffusers import WanPipeline
from diffusers.utils import export_to_video

MODEL_ID = "Wan-AI/Wan2.2-TI2V-5B-Diffusers"
MODEL_REVISION = os.getenv("CINEFORGE_MODEL_REVISION", "").strip()
NEGATIVE_PROMPT = (
    "overexposed, underexposed, static image, text, subtitles, watermark, logo, "
    "low quality, jpeg artifacts, severe flicker, warped geometry, morphing, duplicate objects"
)

_PIPE = None
_PIPE_ERROR: str | None = None


def _sha256_file(path: str) -> str:
    h = sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_pipeline() -> WanPipeline:
    global _PIPE, _PIPE_ERROR
    if _PIPE is not None:
        return _PIPE
    if not MODEL_REVISION:
        raise RuntimeError("CINEFORGE_MODEL_REVISION must be an immutable Hub commit SHA")
    try:
        pipe = WanPipeline.from_pretrained(
            MODEL_ID,
            revision=MODEL_REVISION,
            dtype=torch.bfloat16,
        )
        # ZeroGPU provides CUDA emulation outside @spaces.GPU and real CUDA inside it.
        pipe.to("cuda")
        _PIPE = pipe
        return pipe
    except Exception as exc:
        _PIPE_ERROR = f"{type(exc).__name__}: {exc}"
        raise


def health() -> str:
    payload = {
        "service": "cineforge-hf-zerogpu-smoke",
        "model_id": MODEL_ID,
        "revision_pinned": bool(MODEL_REVISION),
        "pipeline_loaded": _PIPE is not None,
        "pipeline_error": _PIPE_ERROR,
        "policy": "experimental_smoke_only",
    }
    return json.dumps(payload, sort_keys=True)


@spaces.GPU(size="large", duration=270)
def render_smoke(prompt: str, seed: int, steps: int) -> tuple[str, str]:
    prompt = (prompt or "").strip()
    if len(prompt) < 20:
        raise gr.Error("Original prompt must contain at least 20 characters")
    steps = max(8, min(int(steps), 24))
    seed = int(seed) % (2**31 - 1)

    pipe = _load_pipeline()
    started = time.monotonic()
    generator = torch.Generator(device="cuda").manual_seed(seed)

    # 81 frames at 24 fps = 3.375 s, inside CineForge's 3–5 s smoke contract.
    frames = pipe(
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        height=1280,
        width=704,
        num_frames=81,
        num_inference_steps=steps,
        guidance_scale=5.0,
        generator=generator,
    ).frames[0]

    out_dir = Path(tempfile.mkdtemp(prefix="cineforge-smoke-"))
    output_path = str(out_dir / "smoke.mp4")
    export_to_video(frames, output_path, fps=24)
    elapsed = time.monotonic() - started

    props = torch.cuda.get_device_properties(0)
    metadata = {
        "provider": "huggingface_zerogpu_large",
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_identity_sha256": sha256(f"{MODEL_ID}@{MODEL_REVISION}".encode()).hexdigest(),
        "prompt_sha256": sha256(prompt.encode()).hexdigest(),
        "output_sha256": _sha256_file(output_path),
        "seed": seed,
        "steps": steps,
        "requested_frames": 81,
        "fps": 24,
        "nominal_duration_s": 81 / 24,
        "width": 704,
        "height": 1280,
        "gpu_name": props.name,
        "gpu_vram_gb": round(props.total_memory / 1024**3, 2),
        "render_elapsed_s": round(elapsed, 3),
        "evidence_status": "RENDERED_QC_PENDING",
    }
    return output_path, json.dumps(metadata, indent=2, sort_keys=True)


with gr.Blocks(title="CineForge ZeroGPU Smoke Worker") as demo:
    gr.Markdown("# CineForge ZeroGPU Smoke Worker\nGoverned 3–5 second original-video smoke rendering. QC is performed downstream.")
    prompt = gr.Textbox(label="Original cinematic prompt", lines=6)
    with gr.Row():
        seed = gr.Number(label="Seed", value=321, precision=0)
        steps = gr.Slider(label="Inference steps", minimum=8, maximum=24, value=16, step=1)
    run = gr.Button("Run governed smoke render", variant="primary")
    video = gr.Video(label="Smoke output")
    metadata = gr.Code(label="Runtime metadata", language="json")
    run.click(render_smoke, inputs=[prompt, seed, steps], outputs=[video, metadata], api_name="smoke")
    gr.Textbox(value=health, label="Health", every=30)


demo.queue(max_size=4).launch()
