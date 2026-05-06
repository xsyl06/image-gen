<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&text=image-gen&fontSize=50&fontAlignY=35&desc=AI%20Image%20Generation%20Pipeline&descAlignY=55&fontColor=ffffff" width="100%" />

[English](README.md) | [中文](docs/README.zh-CN.md)

</div>

<!-- readme-gen:start:badges -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Dependencies-Zero-brightgreen?style=flat" alt="Zero Dependencies" />
  <img src="https://img.shields.io/badge/ComfyUI-Required-orange?style=flat" alt="ComfyUI" />
</p>
<p align="center">
  <img src="https://skillicons.dev/icons?i=python,git,github&theme=dark" alt="Tech Stack" />
</p>
<!-- readme-gen:end:badges -->

---

> Transform natural language into high-quality images through a structured 6-step AI pipeline — powered by a Prompt Knowledge Graph and iterative vision-model evaluation.

**image-gen** is an end-to-end image generation engine that takes a simple text description and produces refined, high-quality images. It uses a knowledge graph to enrich prompts, submits them to ComfyUI for generation, then evaluates results with a multimodal vision model and iterates until quality thresholds are met.

> You need to install ComfyUI and the corresponding model in advance. For specific installation instructions, please refer to [install-guide](docs/install-guide.md)

---

## Highlights

<table>
<tr>
<td width="50%" valign="top">

### Structured Prompts
A 14-dimension JSON prompt schema covering subject, style, mood, composition, lighting, and more — giving fine-grained control over generation.

</td>
<td width="50%" valign="top">

### Prompt Knowledge Graph
A co-occurrence-based entity recommendation system that suggests complementary style, mood, and lighting attributes from seed keywords.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### Iterative Refinement
A vision model scores each generation on 6 dimensions (subject accuracy, style fidelity, mood, composition, technical quality, overall satisfaction) and feeds back an improved prompt.

</td>
<td width="50%" valign="top">

### Zero External Dependencies
The entire core engine uses only Python standard library — `urllib`, `json`, `pathlib`. No `pip install` required.

</td>
</tr>
</table>

---

## Pipeline

```
Natural Language
       │
       ▼
┌─────────────────┐
│  1. Intent       │  ── Extract seed entities
│  Recognition     │     (LLM + keyword fallback)
└────────┬────────┘
         ▼
┌─────────────────┐
│  2. KG Query     │  ── Recommend complementary entities
│  (Skeleton)      │     via co-occurrence statistics
└────────┬────────┘
         ▼
┌─────────────────┐
│  3. Prompt       │  ── Assemble 14-dimension JSON prompt
│  Generation      │     → convert to text format
└────────┬────────┘
         ▼
┌─────────────────┐
│  4. ComfyUI      │  ── Submit workflow, poll, download
│  Generation      │     generated images
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. Evaluation   │  ── Vision model scores 6 dimensions
│  Loop            │     if score < threshold → refine & retry
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. Experience   │  ── Record successful combinations
│  Accumulation    │     back into the Knowledge Graph
└─────────────────┘
```

---

## Quick Start

### Install as a Claude Code Skill (Recommended)

This project is a **Claude Code skill** — once installed, Claude can orchestrate the full image generation pipeline for you through natural conversation.

**Global install** (available in all your Claude Code sessions):

```bash
# 1. Clone the repo
git clone git@github.com:xsyl06/image-gen.git

# 2. Copy the skill directory to ~/.claude/skills/
cp -r image-gen/image-gen ~/.claude/skills/image-gen

# 3. (Optional) If you already have ComfyUI workflows, symlink or copy them:
#    cp -r /path/to/your/workflows ~/.claude/skills/image-gen/scripts/engine/workflows/

# 4. Edit config.json with your ComfyUI and vision API settings:
cd ~/.claude/skills/image-gen
# Edit scripts/engine/config.json (see Configuration below)
```

After installing, restart Claude Code. The skill activates automatically — just describe the image you want:

```
User: 生成一张赛博朋克风格的城市夜景
User: Generate a watercolor painting of a cat reading a book
```

**Per-project install** (only active inside this repo):

```bash
git clone git@github.com:xsyl06/image-gen.git
cd image-gen
# The SKILL.md in the project root activates the skill when you open Claude Code here
```

---

### Prerequisites

- **Python 3.8+** — no external packages needed
- **ComfyUI** running on `127.0.0.1:8188` ([installation guide](references/install-guide.md))
- A vision/chat model with an **OpenAI-compatible API** (for intent recognition and image evaluation)

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
  "default_workflow": "workflows/ernie_image_gguf"
}
```

> **Security tip**: Set `VISION_API_KEY` as an environment variable rather than writing it into config.json.

### Run

```bash
python scripts/image-gen.py "a cat reading a book"

# With options
python scripts/image-gen.py "a cat" --iterations 5 --threshold 9
python scripts/image-gen.py "a cat" --config custom.json
```

---

## Project Structure

```
image-gen/
├── scripts/
│   ├── image-gen.py              # CLI entry point
│   └── engine/
│       ├── intent.py             # LLM intent recognition + keyword fallback
│       ├── kg/
│       │   ├── engine.py         # PromptKG — knowledge graph engine
│       │   └── data/             # Entity definitions & co-occurrence data
│       ├── json_prompt.py        # 14-dimension JSON prompt schema
│       ├── prompt_assembly.py    # Prompt assembly from KG skeleton
│       ├── comfyui.py            # ComfyUI HTTP client (submit/poll/download)
│       ├── evaluator.py          # Vision-based 6-dimension image evaluation
│       ├── workflow_loader.py    # Workflow template loading & injection
│       ├── kg_update.py          # Experience accumulation back into KG
│       ├── config.json           # Configuration
│       └── workflows/            # ComfyUI workflow templates
├── references/                   # Documentation
└── output/                       # Generated images
```

---

## Core Modules

| Module | Role |
|--------|------|
| `intent.py` | Parses natural language into KG seed entities (LLM or keyword fallback) |
| `kg/engine.py` | Knowledge graph — entity recommendation via co-occurrence statistics |
| `json_prompt.py` | 14-dimension structured prompt schema and text conversion |
| `prompt_assembly.py` | Assembles full prompts from KG skeleton and user intent |
| `comfyui.py` | ComfyUI HTTP client — submit workflows, poll status, download images |
| `evaluator.py` | Vision model evaluation with 6-dimension weighted scoring |
| `workflow_loader.py` | Loads and configures ComfyUI workflow templates |
| `kg_update.py` | Records successful prompt-entity combinations back into the KG |

---

## Documentation

| Document | Description |
|----------|-------------|
| [Pipeline](references/pipeline.md) | Complete 6-step pipeline walkthrough |
| [Prompt Schema](references/prompt-schema.md) | 14-dimension JSON prompt specification |
| [Install Guide](references/install-guide.md) | ComfyUI setup instructions |

---

## Architecture

- **Zero external dependencies** — every module uses only Python standard library
- **Knowledge graph** — JSON-based entity definitions with co-occurrence statistics for intelligent prompt enrichment
- **Structured prompts** — a 14-dimension schema (subject, style, mood, composition, lighting, background, color palette, quality tags, aspect ratio, resolution, negative prompt, weight emphasis, Chinese typography DSL, confrontation composition)
- **Vision-model evaluation** — 6-dimension weighted scoring with iterative prompt refinement
- **ComfyUI integration** — HTTP-based workflow submission, polling, and image download
- **Chinese typography support** — Built-in Chinese text layout DSL for poster/typography generation

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%" />

</div>
