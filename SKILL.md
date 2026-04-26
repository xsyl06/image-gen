---
name: image-gen
description: AI image generation skill. Transforms natural language descriptions into structured prompts and generates images via ComfyUI. Use whenever the user asks to generate, create, draw, or make an image — even if they don't explicitly say "generate image". Also triggers on /img commands, when users describe a scene with a style preference, or want to produce visual content (posters, covers, illustrations, photos, art). If the user mentions ComfyUI, stable diffusion, or image generation at all, use this skill.
---

# Image-Gen — AI Image Generation

## How to Use This Skill

When the user requests an image, follow the 6-step pipeline below. Each step explains what to do and which module to call.

**Pipeline:** Intent → KG Query → Prompt Assembly → ComfyUI Generation → Evaluation Loop → KG Update

---

## Step 1: Intent Recognition — Extract Seed Entities

Parse the user's natural language description into KG entity tags. Use your own understanding — don't rely on keyword matching.

### How to extract entities

1. Read the user's description carefully.
2. Identify entities in these categories and map them to KG tags:

| Category | KG tag prefix | Example |
|----------|--------------|---------|
| Subject | `subject:` | "a cat" → `subject:cat` |
| Style | `style:` | "watercolor" → `style:watercolor` |
| Mood | `mood:` | "peaceful" → `mood:peaceful` |
| Composition | `composition:` | "close-up" → `composition:close_up` |
| Lighting | `lighting:` | "natural light" → `lighting:natural` |
| Background | `background:` | "indoor" → `background:indoor` |
| Color palette | `color_palette:` | "warm tones" → `color_palette:warm` |
| Genre | `genre:` | "poster" → `genre:poster` |

3. Available entities are defined in `engine/kg/data/prompt-graph.json` — read it to see what tags exist.
4. If the user mentions something not in the KG, still include it — the skeleton will handle unknowns gracefully.

### Output

A list of seed entity tags, e.g.: `["subject:cat", "style:watercolor", "mood:warm"]`

---

## Step 2: KG Query — Get Skeleton Recommendations

Use the PromptKG engine to get dimension recommendations for unfilled categories.

```python
import sys
from pathlib import Path

# Add engine to path
ENGINE_DIR = Path("engine")  # or full path from skill location
sys.path.insert(0, str(ENGINE_DIR))

from kg.engine import PromptKG

kg = PromptKG()
skeleton = kg.skeleton(seeds)  # seeds from Step 1
```

### What skeleton returns

```json
{
  "seeds": ["subject:cat", "style:watercolor"],
  "filled": {
    "subject": {"entity": "subject:cat", "name": "猫"},
    "style": {"entity": "style:watercolor", "name": "水彩"}
  },
  "recommendations": {
    "mood": [{"entity": "mood:warm", "score": 52, "confidence": 0.43}, ...],
    "lighting": [{"entity": "lighting:natural", ...}, ...]
  },
  "example_prompts": [...]
}
```

- `filled`: Categories the seeds already cover
- `recommendations`: Top 3 entity suggestions for each unfilled category, ranked by co-occurrence confidence
- `example_prompts`: Matching prompts from the prompt_index

Pick the top recommendation from each category you want to fill.

---

## Step 3: Prompt Assembly — Build JSON Prompt

Assemble a JSON prompt from skeleton recommendations + user intent details.

### 14-Dimension Schema

The JSON prompt supports these fields (all optional, use what fits):

| Field | Type | When to use |
|-------|------|-------------|
| `subject` | string/object | Main subject (recommended) |
| `style` | string/object | Artistic style (recommended) |
| `mood` | string/object | Emotional atmosphere (recommended) |
| `composition` | object | Framing, angle, layout |
| `lighting` | object | Light source and quality |
| `background` | object | Setting and environment |
| `color_palette` | object | Color scheme |
| `text_content` | object | Text to render in image |
| `layout` | string/object | Text layout (required if text_content exists) |
| `typography_layout` | object | Chinese typography DSL |
| `confrontation` | object | Left/right or top/bottom comparison |
| `technical_specs` | object | Quality and rendering params |
| `negative_constraints` | list | Things to avoid (recommended) |
| `aspect_ratio` | string | "1:1", "3:4", "16:9", etc. |

See `references/prompt-schema.md` for detailed examples of each field.

### Assembly rules

1. Fill `filled` categories from skeleton directly:
   ```python
   for category, entity_info in skeleton["filled"].items():
       tag = entity_info["entity"]  # e.g. "subject:cat"
       value = tag.split(":")[-1]   # e.g. "cat"
       json_prompt[category] = value
   ```

2. Add top recommendations for unfilled categories:
   ```python
   for category, recs in skeleton["recommendations"].items():
       if recs:
           json_prompt[category] = recs[0]["entity"].split(":")[-1]
   ```

3. Enrich with user intent details — add details from the user's description that didn't map to KG entities.

4. Always include `negative_constraints`:
   ```json
   ["blurry", "distorted", "ugly", "watermark", "low quality"]
   ```

5. Add `aspect_ratio` if the user specifies one (default: "3:4" for portraits, "16:9" for landscapes).

---

## Step 4: Convert to Text + ComfyUI Generation

### 4a. Convert JSON prompt to text

```python
from json_prompt import json_prompt_to_text

result = json_prompt_to_text(json_prompt)
positive = result["positive"]   # ComfyUI positive prompt
negative = result["negative"]   # ComfyUI negative prompt
meta = result["meta"]           # Flags like has_text_content, has_typography_layout
```

### 4b. Inject prompt into ComfyUI workflow

Use the workflow loader to load and inject prompts automatically:

```python
from workflow_loader import load_workflow, inject_prompts

# Load from engine/workflows/ directory
workflow = load_workflow("default_workflow.json")  # or any .json file name

# Or load from config
workflow_name = cfg.get("default_workflow", "default_workflow.json")
workflow = load_workflow(workflow_name)

# Inject prompts
workflow = inject_prompts(workflow, positive, negative)
```

If no workflow exists in `engine/workflows/`, ask the user to export one from ComfyUI:

1. Open ComfyUI in browser (`http://127.0.0.1:8188`)
2. Set up the desired workflow
3. Click the gear icon → "Save (API format)"
4. Save the JSON to `engine/workflows/` (e.g. `default_workflow.json`)

Available workflows:

```python
from workflow_loader import list_workflows
print(list_workflows())  # e.g. ["default_workflow.json", "sdxl_workflow.json"]
```

### 4c. Submit and generate

```python
from comfyui import check_connection, generate_image

cfg = load_config()  # from engine/config.json

if not check_connection(cfg):
    # Tell user: ComfyUI not running. Start with: python main.py --port 8188
    raise ConnectionError("Cannot connect to ComfyUI")

result = generate_image(workflow, cfg, filename_prefix="gen")
# result = {"prompt_id": "...", "filepaths": [...]}
```

---

## Step 5: Evaluation Loop

Use the vision model to score the generated image and refine the prompt iteratively.

### Evaluation prompt

Ask the vision model to score on 6 dimensions (1-10 scale):

```
Evaluate this generated image against the user's original request:
"{user_intent}"

Score each dimension 1-10:
1. Subject Accuracy: Does the image match the described subject?
2. Style Fidelity: Is the artistic style correctly rendered?
3. Mood/Atmosphere: Does it convey the intended mood?
4. Composition Quality: Is the layout well-structured?
5. Technical Quality: Resolution, clarity, detail level
6. Overall Satisfaction: General aesthetic appeal

Also provide:
- weighted_score: Subject(0.25) + Style(0.20) + Mood(0.15) + Composition(0.15) + Technical(0.15) + Overall(0.10)
- strengths: List of what works well
- weaknesses: List of issues to fix
- improved_prompt: Specific prompt text that would address the weaknesses

Return as JSON.
```

### Loop logic

```python
runs = []
for i in range(1, cfg["max_iterations"] + 1):
    # Generate image (Step 4)
    result = generate_image(workflow, cfg, filename_prefix=f"run-{i:03d}")
    
    # Evaluate with vision model
    evaluation = describe_image(
        result["filepaths"][0],
        evaluation_prompt,  # prompt above
        cfg
    )
    
    runs.append({
        "run": i,
        "image": result["filepaths"][0],
        "evaluation": evaluation
    })
    
    if evaluation.get("weighted_score", 0) >= cfg["score_threshold"]:
        break  # Passes threshold, stop iterating
    
    # Improve prompt based on feedback
    improved_text = evaluation.get("improved_prompt", "")
    if improved_text:
        positive = improved_text  # Use improved prompt for next iteration
```

### Memory management

If doing multiple consecutive generations, call `free_memory(cfg)` between runs to avoid VRAM accumulation that causes quality degradation (extra limbs, distorted details):

```python
from comfyui import free_memory
free_memory(cfg, unload_models=False)  # Fast: free unused memory
# or
free_memory(cfg, unload_models=True)   # Slower but cleanest: unload all models
```

---

## Step 6: KG Update — Accumulate Experience

After a successful generation (score >= threshold), record the prompt combination in the KG for future reference.

### What to update

1. **Increment co-occurrence counts** for entity pairs used in the successful prompt
2. **Add a new prompt_index entry** if this is a novel combination

### How to update

```python
import json
from pathlib import Path
from itertools import combinations

GRAPH_PATH = Path("engine/kg/data/prompt-graph.json")

def update_kg(kg, used_entities, score):
    if score < cfg["score_threshold"]:
        return  # Only record successful generations
    
    # Load current graph
    with open(GRAPH_PATH, "r") as f:
        graph = json.load(f)
    
    # Increment co-occurrence for each pair
    for e1, e2 in combinations(used_entities, 2):
        if e1 not in graph["co_occurrence"]:
            graph["co_occurrence"][e1] = {}
        if e2 not in graph["co_occurrence"][e1]:
            graph["co_occurrence"][e1][e2] = 0
        graph["co_occurrence"][e1][e2] += 1
    
    # Add to prompt_index if novel
    existing_tags = {
        frozenset(p["tags"]) for p in graph.get("prompt_index", [])
    }
    if frozenset(used_entities) not in existing_tags:
        graph["prompt_index"].append({
            "id": f"p-{len(graph['prompt_index']) + 1:03d}",
            "title": "Generated from user request",
            "title_zh": "",
            "tags": list(used_entities),
            "prompt_short": positive[:100],
            "prompt_short_zh": ""
        })
    
    # Save
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False)
```

---

## Configuration

Read `engine/config.json` for settings:

| Key | Default | Purpose |
|-----|---------|---------|
| `comfyui_host` | `127.0.0.1` | ComfyUI server address |
| `comfyui_port` | `8188` | ComfyUI server port |
| `output_dir` | `~/image-gen-output` | Where generated images are saved |
| `vision_model` | `{...}` | Vision model config (OpenAI-compatible API) |
| `max_iterations` | `3` | Maximum evaluation loop iterations |
| `score_threshold` | `8` | Passing score threshold (1-10 scale) |

The `vision_model` section configures an OpenAI-compatible API:
- `type`: "openai"
- `base_url`: API endpoint
- `model`: Model name (e.g., "qwen3.6-plus")
- `api_key_env`: API key

---

## Common Workflows

### Simple generation

```
User: /img "a sunset over mountains, oil painting style"
```

1. Extract seeds: `["subject:landscape", "style:oil_painting", "lighting:golden_hour"]`
2. Get skeleton recommendations
3. Assemble JSON prompt
4. Convert to text, inject into workflow, generate
5. Evaluate, iterate if needed
6. Update KG

### Text in image

```
User: /img "一张咖啡海报，上面写着'秋日味道'"
```

1. Detect text requirement → add `text_content` and `layout` fields
2. Use `typography_layout` for Chinese text positioning
3. Follow Steps 2-6 as normal
4. Validate: `layout` is required when `text_content` exists

### Comparison/contrast image

```
User: /img "健康饮食和垃圾食品的对比"
```

1. Use `confrontation` field with `left_vs_right` or `top_vs_bottom` layout
2. Fill left/right (or top/bottom) details
3. Follow Steps 2-6 as normal

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to ComfyUI | Tell user to start: `python main.py --port 8188` |
| ComfyUI execution error | Check workflow JSON structure, simplify if needed |
| Vision API not configured | Skip evaluation, tell user to set up `vision_model` in config |
| Quality degrades after multiple runs | Call `free_memory(cfg)` between generations |
| No entities found in intent | Default to `["subject:cat"]` and ask user for clarification |

---

## See Also

- `references/prompt-schema.md` — Detailed 14-dimension JSON prompt schema with examples
- `references/pipeline.md` — Complete pipeline walkthrough with error handling
- `references/install-guide.md` — ComfyUI installation instructions
