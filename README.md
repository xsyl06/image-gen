# image-gen

AI image generation pipeline that transforms natural language descriptions into high-quality images through a structured 6-step process.

## Pipeline Flow

```
Natural Language → Intent Recognition → KG Query → Prompt Generation → ComfyUI Generation → Evaluation Loop → KG Update
```

## Quick Start

### Prerequisites

- Python 3.8+ (no external dependencies — stdlib only)
- A running ComfyUI server (default: `127.0.0.1:8188`)
- A vision/chat model with OpenAI-compatible API (for intent recognition and evaluation)

### Configuration

Edit `scripts/engine/config.json`:

```json
{
  "comfyui_host": "127.0.0.1",
  "comfyui_port": 8188,
  "output_dir": "~/image-gen-output",
  "vision_api_url": "https://your-api-endpoint/v1",
  "vision_model": "qwen3.6-plus",
  "vision_api_key": "",
  "max_iterations": 3,
  "score_threshold": 8,
  "default_workflow": "workflows/image_z_image_gguf.json"
}
```

> **Security**: Set `VISION_API_KEY` environment variable instead of writing it in config.json.

### Usage

```bash
python scripts/image-gen.py "a cat reading a book"
python scripts/image-gen.py "a cat" --iterations 5 --threshold 9
python scripts/image-gen.py "a cat" --config custom.json
```

## Directory Structure

```
image-gen/
├── scripts/
│   ├── image-gen.py          # CLI entry point
│   └── engine/
│       ├── comfyui.py        # ComfyUI HTTP client
│       ├── json_prompt.py    # 14-dimension JSON prompt schema
│       ├── evaluator.py      # Vision-based image evaluation
│       ├── intent.py         # LLM intent recognition + keyword fallback
│       ├── workflow_loader.py # Workflow loading and prompt injection
│       ├── prompt_assembly.py # JSON prompt assembly
│       ├── kg_update.py      # Knowledge graph experience accumulation
│       ├── config.json       # Configuration
│       └── kg/
│           ├── engine.py     # PromptKG knowledge graph
│           └── data/         # Entity and co-occurrence data
└── docs/                     # Documentation
```

## Core Modules

| Module | Description |
|--------|-------------|
| `intent.py` | Extracts KG seed entities from natural language (LLM + keyword fallback) |
| `kg/engine.py` | Knowledge graph for prompt entity recommendation |
| `json_prompt.py` | 14-dimension structured prompt schema and text converter |
| `comfyui.py` | ComfyUI HTTP client (submit/poll/download) |
| `evaluator.py` | Vision model evaluation with 6-dimension scoring |
| `kg_update.py` | Records successful generations back into the KG |

## Architecture

- **Zero external dependencies**: Core engine uses only Python stdlib (`urllib`, `json`, `pathlib`)
- **Structured prompts**: JSON prompt schema with 14 dimensions (subject, style, mood, composition, etc.)
- **Knowledge graph**: Entity recommendation based on co-occurrence statistics
- **Iterative refinement**: Evaluation loop with vision model feedback and prompt improvement
- **Chinese support**: Full Chinese typography DSL and entity bilingual naming
