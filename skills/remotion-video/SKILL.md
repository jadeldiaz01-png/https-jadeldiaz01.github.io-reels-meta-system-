---
name: remotion-video
version: 1.0.0
domain: video
---
# Remotion Video Skill

Build and validate short-form video plans compatible with a Remotion production pipeline. Use typed scene/caption/render inputs, preserve asset provenance, and treat rendering/publishing as separate controlled actions.

## Workflow
1. Validate the video request and rights metadata.
2. Produce composition, scene, caption and render-plan JSON.
3. Keep captions in structured JSON with text/start/end/timestamp/confidence fields.
4. Run render validation before release.
5. Never publish from this skill; publication must go through the external-action controller and policy gates.

## Success
Output validates against the schema and emits evidence describing inputs, composition settings and QA checks.
