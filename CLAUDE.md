# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**image-gen** is an AI image generation pipeline that transforms natural language descriptions into high-quality images through a structured 6-step process: Intent Recognition → KG Query → Prompt Generation → ComfyUI Generation → Evaluation Loop → Experience Accumulation.

The project uses only Python standard library — zero external dependencies for the core engine.

## Directory Structure

```
image-gen/
├── scripts/
│   ├── image-gen.py          # CLI entry point
│   └── engine/
│       ├── comfyui.py                # ComfyUI HTTP client (submit/poll/download)
│       ├── json_prompt.py            # JSON prompt schema + converter to text
│       ├── config.json               # Configuration (host, port, vision model, thresholds)
│       ├── kg/
│       │   ├── engine.py             # PromptKG — knowledge graph for prompt entities
│       │   └── data/
│       │       ├── prompt-graph.json # Entity definitions + co-occurrence data
│       │       └── extensions.json   # Additional entity data
└── references/
    ├── install-guide.md          # ComfyUI installation instructions
    ├── prompt-schema.md          # 14-dimension JSON prompt schema docs
    └── pipeline.md               # Complete 6-step pipeline documentation
```

## Core Modules

### `scripts/image-gen.py` — CLI Entry Point

```bash
python scripts/image-gen.py "a cat reading a book"
python scripts/image-gen.py "a cat" --iterations 5 --threshold 9
python scripts/image-gen.py "a cat" --config custom.json
```

Key functions: `extract_seed_entities()` (keyword-based intent parsing), `assemble_json_prompt()`, `run_generation()`.

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

## Configuration

Edit `scripts/engine/config.json`:
- `comfyui_host` / `comfyui_port` — ComfyUI server (default: `127.0.0.1:8188`)
- `output_dir` — Image output directory (default: `~/image-gen-output`)
- `vision_model` — Vision model for evaluation (uses OpenAI-compatible API)
- `max_iterations` — Max refinement iterations (default: 3)
- `score_threshold` — Quality threshold (default: 8/10)

## Architecture Notes

- **Zero external dependencies**: All modules use only Python stdlib (`urllib`, `json`, `pathlib`, etc.)
- **Prompt flow**: Natural language → seed entities → KG skeleton → JSON prompt (14 dims) → text prompt → ComfyUI
- **KG data**: Entities and co-occurrence data stored as JSON files in `scripts/engine/kg/data/`
- **Extensible**: Extensions can be merged via `extensions.json`; templates loaded from `scripts/engine/templates/` directory
- The CLI's `extract_seed_entities()` uses simple keyword matching — a full implementation would use LLM-based intent parsing
