---
name: image-gen
description: AI image generation skill. Transforms natural language descriptions into structured prompts and generates images via ComfyUI. Use whenever the user asks to generate, create, draw, or make an image — even if they don't explicitly say "generate image". When users describe a scene with a style preference, or want to produce visual content (posters, covers, illustrations, photos, art). If the user mentions ComfyUI, stable diffusion, or image generation at all, use this skill.
---

# Image-Gen — AI Image Generation

## Quick Start

For most requests, run the full pipeline in one command:

```bash
python scripts/image-gen-cli.py pipeline --prompt "用户描述"
```

This runs all 6 steps automatically: Intent → KG Query → Prompt Assembly → ComfyUI Generation → Evaluation Loop → KG Update.

For step-by-step control, see the commands below.

---

## Step 0: Brainstorm & Clarify

Before running the pipeline, analyze the user's description for **missing or ambiguous** visual dimensions. If the description is already rich and specific (covers style, lighting, mood, composition, color, etc.), skip this step and proceed directly to Step 1.

Otherwise, follow this two-phase flow:

### Phase 1: Plan Questions Internally

Analyze the user's description against these dimensions:

| Dimension | Key |
|---|---|
| Artistic style | `style` |
| Mood / atmosphere | `mood` |
| Lighting | `lighting` |
| Composition | `composition` |
| Color palette | `color_palette` |
| Background / scene | `background` |
| Genre / purpose | `genre` |
| Aspect ratio | `aspect_ratio` |

For each dimension that is **not mentioned or is vague**, draft a question with 3-5 concrete options. Prioritize by impact: `style` > `lighting` > `composition` > `mood` > `color_palette` > others.

Plan 2-4 questions total. Do NOT show the list to the user — keep it internal.

### Phase 2: Ask One by One

Ask questions **one at a time**. Each question should:
- Be short and conversational (1-2 sentences)
- Offer 3-5 concrete options as suggestions, plus "其他（请描述）" / "Other (describe)" as the last option
- Use the same language as the user's input
- Wait for the user's answer before asking the next question

Example flow:
```
Claude: 你希望什么风格？（写实摄影 / 油画 / 水彩 / 数字插画 / 其他）
User: 写实摄影

Claude: 光影偏好？（自然光 / 金色黄昏 / 棚拍灯光 / 阴天柔光 / 其他）
User: 金色黄昏

Claude: 构图呢？（特写 / 半身 / 全身 / 场景全景 / 其他）
User: 特写
```

After all questions are answered, **merge** the user's answers into their original description to form an enhanced prompt, then proceed to Step 1.

```
Original: "一只猫"
Answers: style=写实摄影, lighting=金色黄昏, composition=特写
Enhanced: "一只猫，写实摄影，金色黄昏光影，特写构图"
```

---

## Step 1: Extract Seed Entities

Map the user's description into KG entity tags. You can either:

**A) Use the CLI** (calls LLM-based extraction):
```bash
python scripts/image-gen-cli.py intent --text "a watercolor cat"
# Output: ["style:watercolor", "subject:cat"]
```

**B) Extract manually** — identify entities by category:

| Category | Prefix | Example |
|---|---|---|
| Subject | `subject:` | "a cat" → `subject:cat` |
| Style | `style:` | "watercolor" → `style:watercolor` |
| Mood | `mood:` | "peaceful" → `mood:peaceful` |
| Composition | `composition:` | "close-up" → `composition:close-up` |
| Lighting | `lighting:` | "sunlight" → `lighting:sunlight` |
| Background | `background:` | "indoor" → `background:indoor` |
| Color palette | `color_palette:` | "warm" → `color_palette:warm` |
| Color | `color:` | "red" → `color:red` |
| Genre | `genre:` | "poster" → `genre:poster` |
| Technique | `technique:` | "origami" → `technique:origami folding` |
| Texture | `texture:` | "rough" → `texture:rough` |
| Theme | `theme:` | "cyberpunk" → `theme:cyberpunk` |

Available entities: `scripts/engine/kg/data/prompt_graph.json`. If something isn't in the KG, still include it — the skeleton handles unknowns gracefully.

---

## Step 2: KG Query — Get Recommendations

```bash
# Via stdin pipe:
echo '["subject:cat", "style:watercolor"]' | python scripts/image-gen-cli.py skeleton --stdin

# Or inline:
python scripts/image-gen-cli.py skeleton --seeds '["subject:cat", "style:watercolor"]'
```

Returns `filled` (categories already covered) and `recommendations` (top 3 suggestions per unfilled category). Pick the top recommendation from each category you want to fill.

---

## Step 3: Assemble JSON Prompt

```bash
python scripts/image-gen-cli.py assemble \
  --skeleton '<skeleton_json>' \
  --seeds '["subject:cat", "style:watercolor"]' \
  --intent "a watercolor cat"
```

The JSON prompt supports these fields (all optional):

| Field | When to use |
|---|---|
| `subject` | Main subject (recommended) |
| `style` | Artistic style (recommended) |
| `mood` | Emotional atmosphere (recommended) |
| `composition` / `lighting` / `background` / `color_palette` | Visual dimensions |
| `text_content` + `layout` | Text to render in image (layout is required when text_content exists) |
| `typography_layout` | Chinese typography DSL |
| `confrontation` | Left/right or top/bottom comparison |
| `technical_specs` | Quality params |
| `negative_constraints` | Always include: `["blurry", "distorted", "ugly", "watermark", "low quality"]` |
| `aspect_ratio` | "1:1", "3:4", "16:9" (default: "3:4" for portraits) |

See `references/prompt-schema.md` for detailed examples.

---

## Step 4: Generate

### 4a. Convert to text
```bash
python scripts/image-gen-cli.py convert --prompt '<json_prompt>'
# Output: {"positive": "...", "negative": "...", "meta": {}}
```

### 4b. Inject into workflow
```bash
python scripts/image-gen-cli.py inject \
  --workflow ernie_image_gguf.json \
  --positive "..." --negative "..."
```

List available workflows: `python scripts/image-gen-cli.py list-workflows`

### 4c. Submit to ComfyUI
```bash
python scripts/image-gen-cli.py generate \
  --workflow ernie_image_gguf.json \
  --positive "..." --negative "..." \
  --prefix my-gen
# Output: {"prompt_id": "...", "filepaths": ["/path/to/image.png"]}
```

If ComfyUI isn't running, tell the user: `python main.py --port 8188`

---

## Step 5: Evaluate & Iterate

```bash
python scripts/image-gen-cli.py evaluate \
  --image /path/to/image.png \
  --intent "原始描述"
# Output: {weighted_score, strengths, weaknesses, improved_prompt}
```

Scores 1-10 on 6 dimensions: Subject Accuracy (0.25), Style Fidelity (0.20), Mood (0.15), Composition (0.15), Technical (0.15), Overall (0.10).

If `weighted_score < score_threshold` (default 8), use `improved_prompt` to refine and try again. Repeat up to `max_iterations` (default 3).

Between consecutive generations, free VRAM to avoid quality degradation:
```bash
python scripts/image-gen-cli.py free-memory --unload
```

---

## Step 6: Update KG

After a successful generation (score >= threshold), record it in the KG:

```bash
python scripts/image-gen-cli.py update-kg \
  --entities '["subject:cat", "style:watercolor"]' \
  --positive-prompt "cat, watercolor, warm mood..." \
  --score 8.5
```

This increments co-occurrence counts and adds a new prompt_index entry for future recommendations.

---

## Additional Commands

| Command | Purpose |
|---|---|
| `validate --prompt '<json>'` | Validate JSON prompt against schema |
| `describe --image <path> --prompt "问题"` | Analyze image with vision model |
| `compare --image-a <path> --image-b <path> --prompt "问题"` | Compare two images |
| `check` | Check ComfyUI connection status |

All commands accept `--config <path>` to override `engine/config.json`.

---

## Troubleshooting

| Issue | Solution |
|---|---|
| Cannot connect to ComfyUI | Start: `python main.py --port 8188` |
| Vision API not configured | Skip evaluation, set up `vision_model` in `engine/config.json` |
| Quality degrades after multiple runs | Run `free-memory --unload` between generations |
| No entities found | Pipeline extracts subject keywords from user input directly |

---

## See Also

- `references/prompt-schema.md` — 14-dimension JSON prompt schema with examples
- `references/pipeline.md` — Complete pipeline walkthrough with error handling
- `references/install-guide.md` — ComfyUI installation instructions
