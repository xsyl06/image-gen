# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment
The project defaults to using conda for environment control. Use `conda run -n comfyui` to execute commands in the comfyui environment:

```shell
conda run -n comfyui python scripts/image-gen.py "a cat"
conda run -n comfyui python -c "import sys; ..."
conda run -n comfyui python test_script.py
```

Note: `conda activate` requires `conda init` first (modifies shell profiles and is blocked by Claude Code permissions). Use `conda run -n comfyui` instead — it works without init and is the recommended approach for Claude Code.

## Project Overview

**image-gen** is an AI image generation pipeline that transforms natural language descriptions into high-quality images through a structured 6-step process: Intent Recognition → KG Query → Prompt Generation → ComfyUI Generation → Evaluation Loop → Experience Accumulation.

The project uses only Python standard library — zero external dependencies for the core engine.

## Directory Structure

```
image-gen/
├── scripts/
│   ├── image-gen.py              # Legacy single-script entry point
│   ├── image-gen-cli.py          # Unified CLI (subcommands: intent, skeleton, assemble, convert, inject, generate, evaluate, pipeline, etc.)
│   └── engine/
│       ├── comfyui.py            # ComfyUI HTTP client (submit/poll/download)
│       ├── json_prompt.py        # 14-dimension JSON prompt schema + converter to text
│       ├── intent.py             # Intent Recognition — LLM-based entity extraction (fallback: keyword matching)
│       ├── prompt_assembly.py    # Prompt Assembly — build JSON prompt from KG skeleton + seeds
│       ├── evaluator.py          # Evaluation Loop — vision model scoring (6 dimensions) + iterative refinement
│       ├── workflow_loader.py    # Workflow injection — load/modify ComfyUI workflow JSON
│       ├── kg_update.py          # Update KG co-occurrence counts after successful generation
│       ├── config.json           # Configuration (host, port, vision model, thresholds)
│       ├── workflows/            # ComfyUI workflow JSON files (ernie_image_gguf.json, image_z_image_gguf.json)
│       └── kg/
│           ├── engine.py         # PromptKG — knowledge graph for prompt entities
│           └── data/
│               ├── prompt_graph.json  # Entity definitions + co-occurrence data
│               └── extensions.json    # Additional entity data
├── SKILL.md                      # Claude Code skill definition — full pipeline usage docs, commands, and Step 0 brainstorm/clarify flow
├── references/
│   ├── install-guide.md          # ComfyUI + GGUF model installation (mirrors docs/install-guide.md)
│   ├── prompt-schema.md          # 14-dimension JSON prompt schema docs
│   └── pipeline.md               # Complete 6-step pipeline documentation
└── docs/                         # Published documentation (install guide, issues, articles)
```

## Two CLI Entry Points

- **`scripts/image-gen.py`** — Legacy self-contained script. Uses `extract_seed_entities()` (keyword-based) and runs the full pipeline inline. No subcommands.
- **`scripts/image-gen-cli.py`** — Unified CLI with subcommands. Each pipeline step is a separate command (`intent`, `skeleton`, `assemble`, `convert`, `inject`, `generate`, `evaluate`, `pipeline`). Uses `intent.py` (LLM-based extraction with keyword fallback). This is the primary CLI going forward.

## Core Modules

### `scripts/engine/kg/engine.py` — Prompt Knowledge Graph

The `PromptKG` class provides entity recommendation based on seed entities using co-occurrence statistics.

Primary API:
- `kg.skeleton(seeds)` — Generate prompt construction plan from seed entities (main entry point for AI agents)
- `kg.recommend(seeds, target_category)` — Recommend entities for a category given seeds
- `kg.find_prompts(entities)` — Find matching prompt templates
- `kg.validate(entities)` — Check if entity combination is common/moderate/unusual
- `kg.info(entity)` — Entity details + top relations
- `kg.neighbors(entity, category, top_n)` — Co-occurring entities

### `scripts/engine/json_prompt.py` — Structured Prompt Schema

Defines 14-dimension JSON prompt schema (`JSON_PROMPT_SCHEMA`) and converts to text:

- `json_prompt_to_text(json_prompt)` → `{"positive": str, "negative": str, "meta": dict}`
- `validate_json_prompt(json_prompt)` → list of validation issues
- Supports Chinese typography DSL (`typography_layout` field) and confrontation composition (`confrontation` field)

### `scripts/engine/comfyui.py` — ComfyUI HTTP Client

Stdlib-only HTTP client for ComfyUI server:

- `check_connection(cfg)` — Verify ComfyUI is running
- `generate_image(workflow, cfg)` — Submit workflow, poll, download images
- `free_memory(cfg, unload_models=True)` — Free VRAM (fixes quality degradation after consecutive generations)
- `describe_image(image_path, prompt_text, cfg)` — Vision model image analysis
- `compare_images(path_a, path_b, prompt_text, cfg)` — Vision model comparison
- `extract_comfyui_metadata(image_path)` — Extract workflow/prompt from PNG metadata

### `scripts/engine/evaluator.py` — Evaluation Loop

Scores generated images on 6 dimensions (Subject Accuracy, Style Fidelity, Mood, Composition, Technical Quality, Overall) using the configured vision model. Returns `weighted_score`, `strengths`, `weaknesses`, and `improved_prompt`. When score is below threshold, suggests prompt refinements for the next iteration.

### `scripts/engine/intent.py` — Intent Recognition

Extracts KG seed entities from natural language descriptions. Uses the configured vision/chat model (OpenAI-compatible API) when available, falls back to keyword matching. Loads entity catalog from `prompt_graph.json` to ground extraction to known entities while still allowing unknowns.

## Configuration

Edit `scripts/engine/config.json`:
- `comfyui_host` / `comfyui_port` — ComfyUI server (default: `127.0.0.1:8188`)
- `output_dir` — Image output directory (default: `~/image-gen-output`)
- `vision_api_url` / `vision_model` / `vision_api_key` — Vision model for evaluation (OpenAI-compatible API)
- `max_iterations` — Max refinement iterations (default: 3)
- `score_threshold` — Quality threshold (default: 8/10)
- `default_workflow` — Default ComfyUI workflow (default: `workflows/ernie_image_gguf.json`)

Vision API key can also be set via environment variable `VISION_API_KEY` (takes precedence over config file).

## Architecture Notes

- **Zero external dependencies**: All modules use only Python stdlib (`urllib`, `json`, `pathlib`, `re`, etc.)
- **Prompt flow**: Natural language → **brainstorm & clarify (Step 0, orchestrated by SKILL.md)** → seed entities → KG skeleton → JSON prompt (14 dims) → text prompt → ComfyUI
- **KG data**: Entities and co-occurrence data stored as JSON files in `scripts/engine/kg/data/`. The `kg_update.py` module writes back successful generation results to increment co-occurrence counts.
- **Extensible**: Extensions can be merged via `extensions.json`; workflows loaded from `scripts/engine/workflows/` directory
- **SKILL.md**: Defines the Claude Code skill for this project. Contains the full Step 0 brainstorm/clarify flow, all CLI commands, and the `references/` directory pointer. Edit SKILL.md when changing how Claude Code orchestrates image generation.

## Supported Models

Two GGUF-quantized model families (via unsloth):

| Workflow | Main Model | CLIP | VAE | Use Case |
|----------|-----------|------|-----|----------|
| ERNIE-Image | `ernie-image-Q8_0.gguf` | `ministral-3-3b.safetensors` | `flux2-vae.safetensors` | Chinese text rendering, posters, manga |
| Z-Image | `z-image-Q8_0.gguf` | `qwen_3_4b.safetensors` | `ae.safetensors` | Diverse styles, aesthetic imagery |
