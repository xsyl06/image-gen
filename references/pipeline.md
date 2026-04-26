# Image Generation Pipeline

## Overview

The image-gen skill follows a 6-step pipeline to transform natural language descriptions into high-quality images through iterative refinement.

**Pipeline Flow:**
1. Intent Recognition → Seed Entities
2. KG Query → Skeleton Recommendations
3. Prompt Generation → JSON + Text Formats
4. ComfyUI Generation → Image Output
5. Evaluation Loop → Quality Scoring
6. Experience Accumulation → KG Update

---

## Step 1: Intent Recognition

### Purpose
Parse user's natural language description into structured seed entities.

### Input
- `user_intent`: Natural language string (e.g., "a cat reading on windowsill, watercolor style")

### Output
```json
{
  "seed_entities": [
    "subject:cat",
    "style:watercolor",
    "mood:warm"
  ],
  "details": {
    "action": "reading",
    "location": "windowsill"
  }
}
```

### Process
1. Extract subject nouns → `subject:*` entities
2. Identify style keywords → `style:*` entities
3. Detect mood/atmosphere → `mood:*` entities
4. Capture composition hints → `composition:*` entities
5. Note lighting references → `lighting:*` entities

---

## Step 2: KG Query (Skeleton)

### Purpose
Query the Knowledge Graph to get recommendations for unfilled dimensions.

### Input
- `seed_entities`: List of entity tags from Step 1

### Output
```json
{
  "seeds": ["subject:cat", "style:watercolor"],
  "filled": {
    "subject": {"entity": "subject:cat", "name": "Cat"},
    "style": {"entity": "style:watercolor", "name": "Watercolor"}
  },
  "recommendations": {
    "mood": [
      {"entity": "mood:warm", "name": "Warm", "score": 52, "confidence": 0.43},
      {"entity": "mood:peaceful", "name": "Peaceful", "score": 35, "confidence": 0.29}
    ],
    "lighting": [
      {"entity": "lighting:natural", "name": "Natural Light", "score": 35, "confidence": 0.29}
    ],
    "color_palette": [...],
    "composition": [...]
  },
  "example_prompts": [
    {
      "id": "p001",
      "title": "Cozy Cat Watercolor",
      "matched": ["subject:cat", "style:watercolor"],
      "prompt_short": "a cozy cat, watercolor style, warm mood, natural light"
    }
  ]
}
```

### KG API Call
```python
from kg.engine import PromptKG
kg = PromptKG()
skeleton = kg.skeleton(seed_entities)
```

---

## Step 3: Prompt Generation

### Purpose
Assemble full prompt in JSON and text formats.

### Input
- `skeleton`: KG recommendations from Step 2
- `user_intent`: Original user description (for details)

### Output

**JSON Format (14 dimensions):**
```json
{
  "subject": "a cat reading a book",
  "style": "watercolor painting",
  "mood": "warm and cozy",
  "composition": "centered composition",
  "lighting": "natural window light",
  "background": "indoor, windowsill with soft curtains",
  "color_palette": "warm pastel tones",
  "quality_tags": ["high quality", "detailed", "soft edges"],
  "aspect_ratio": "3:4",
  "resolution": "1024x1365",
  "negative_prompt": "blurry, distorted, ugly, deformed",
  "weight emphasis": {
    "subject": 1.2,
    "style": 1.1
  },
  "chinese_layout": null,
  "contrast_composition": null
}
```

**Text Format:**
```
Positive: a cat reading a book on windowsill, watercolor painting, warm and cozy mood, natural window light, indoor background, warm pastel tones, high quality, detailed, soft edges

Negative: blurry, distorted, ugly, deformed
```

### Conversion
```python
from json_prompt import json_prompt_to_text
result = json_prompt_to_text(json_prompt)
positive = result["positive"]
negative = result["negative"]
```

---

## Step 4: ComfyUI Generation

### Purpose
Submit workflow to ComfyUI server and download generated images.

### Input
- `workflow`: ComfyUI workflow JSON (loaded from template)
- `cfg`: Configuration dict (host, port, output_dir)
- `text_prompt`: Positive/negative prompts

### Output
```json
{
  "prompt_id": "abc123-def456",
  "filepaths": [
    "~/image-gen-output/run-001_20260422_182000_0.png"
  ]
}
```

### Process
```python
from comfyui import generate_image, check_connection

# Verify connection
if not check_connection(cfg):
    raise ConnectionError("ComfyUI not running")

# Inject prompt into workflow
workflow = load_workflow_template(cfg.get("workflow_alias", "default"))
workflow["nodes"]["positive_prompt"]["inputs"]["text"] = positive
workflow["nodes"]["negative_prompt"]["inputs"]["text"] = negative

# Generate
result = generate_image(workflow, cfg, filename_prefix="run-001")
```

---

## Step 5: Evaluation Loop

### Purpose
Use multimodal vision model to score image quality and refine prompts iteratively.

### Core Evaluation Loop
```python
def run_generation_loop(user_intent, kg, cfg):
    # Step 1-3: Intent → KG → Prompt
    seed_entities = extract_intent(user_intent)  # LLM
    skeleton = kg.skeleton(seed_entities)
    json_prompt = assemble_json_prompt(skeleton, user_intent)
    text_prompt = json_prompt_to_text(json_prompt)["positive"]

    # Step 4-5: Generation loop
    runs = []
    for i in range(1, cfg["max_iterations"] + 1):
        # Generate
        workflow = load_workflow(cfg.get("workflow_alias", "default"))
        prepared = inject_params(workflow, {"prompt": text_prompt})
        result = generate_image(prepared, cfg, f"run-{i:03d}")

        # Evaluate
        evaluation = evaluate_image(result["filepaths"][0], user_intent, text_prompt, cfg)

        runs.append({
            "run": i,
            "image": result["filepaths"][0],
            "prompt": text_prompt,
            "evaluation": evaluation
        })

        if evaluation["weighted_score"] >= cfg["score_threshold"]:
            break

        # Improve prompt based on evaluation feedback
        text_prompt = evaluation["improved_prompt"]

    return runs
```

### Evaluation Criteria (10-point scale)

**Scoring Dimensions:**
1. **Subject Accuracy** (weight: 0.25): Does the image match the described subject?
2. **Style Fidelity** (weight: 0.20): Is the artistic style correctly rendered?
3. **Mood/atmosphere** (weight: 0.15): Does it convey the intended mood?
4. **Composition Quality** (weight: 0.15): Is the layout well-structured?
5. **Technical Quality** (weight: 0.15): Resolution, clarity, detail level
6. **Overall Satisfaction** (weight: 0.10): General aesthetic appeal

**Evaluation Output:**
```json
{
  "scores": {
    "subject_accuracy": 9,
    "style_fidelity": 8,
    "mood_atmosphere": 7,
    "composition_quality": 8,
    "technical_quality": 9,
    "overall_satisfaction": 8
  },
  "weighted_score": 8.3,
  "feedback": {
    "strengths": ["good subject rendering", "clear watercolor style"],
    "weaknesses": ["slightly dim lighting", "background could be warmer"]
  },
  "improved_prompt": "a cat reading a book on windowsill, watercolor painting, warm and cozy mood, brighter natural window light, indoor background with warm tones, golden hour lighting effect, high quality, detailed",
  "passed": true
}
```

### Threshold
- Default: 8/10
- Maximum iterations: 3 (configurable via `cfg["max_iterations"]`)

---

## Step 6: Experience Accumulation (KG Update)

### Purpose
Record successful prompt combinations in the Knowledge Graph for future reference.

### KG Update Format
```json
{
  "entities": {
    "subject:cat_reading": {
      "category": "subject",
      "name": "Cat Reading",
      "count": 1
    }
  },
  "co_occurrence": {
    "subject:cat": {
      "style:watercolor": 1,
      "mood:warm": 1,
      "lighting:natural": 1,
      "background:indoor_windowsill": 1
    }
  },
  "prompt_index": [
    {
      "id": "p-new-001",
      "title": "Reading Cat on Windowsill",
      "tags": ["subject:cat", "style:watercolor", "mood:warm", "lighting:natural"],
      "prompt_short": "a cat reading on windowsill, watercolor, warm mood, natural light",
      "prompt_short_zh": "窗台读书的猫咪，水彩风格，温暖氛围，自然光"
    }
  ],
  "meta": {
    "updated": "2026-04-22T18:20:00",
    "source": "user_generation_success"
  }
}
```

### Update Process
```python
def update_kg_with_success(kg, prompt_entities, final_prompt, score):
    if score >= 8.0:
        # Increment co-occurrence counts
        for e1, e2 in combinations(prompt_entities, 2):
            kg.increment_co_occurrence(e1, e2)

        # Add to prompt_index if novel combination
        if not kg.find_prompts(prompt_entities):
            kg.add_prompt_index_entry({
                "id": generate_prompt_id(),
                "tags": prompt_entities,
                "prompt_short": final_prompt
            })
```

---

## Error Handling Strategy

### Connection Errors
```python
try:
    if not check_connection(cfg):
        raise ConnectionError("ComfyUI server not reachable")
except Exception as e:
    print(f"Error: {e}")
    print("Please start ComfyUI: python main.py --port 8188")
    return {"error": "comfyui_connection_failed"}
```

### Workflow Execution Errors
```python
try:
    result = generate_image(workflow, cfg)
except RuntimeError as e:
    if "execution error" in str(e):
        print(f"ComfyUI execution failed: {e}")
        # Fallback: use simpler workflow or adjust parameters
        workflow = simplify_workflow(workflow)
        result = generate_image(workflow, cfg)
```

### Vision API Errors
```python
try:
    evaluation = describe_image(image_path, evaluation_prompt, cfg)
except ValueError as e:
    if "Vision API not configured" in str(e):
        print("Warning: Vision evaluation skipped (API not configured)")
        evaluation = {"score": 5.0, "feedback": "manual_evaluation_required"}
```

### Iteration Limit Reached
```python
if i == cfg["max_iterations"] and evaluation["weighted_score"] < cfg["score_threshold"]:
    print(f"Warning: Max iterations reached. Final score: {evaluation['weighted_score']}")
    print("Consider adjusting prompt or increasing max_iterations")
```

---

## Complete Pipeline Example

**User Input:**
```
/img "a cat reading on windowsill, watercolor style"
```

**Step-by-step Execution:**

1. **Intent Recognition:**
   - Seeds: `["subject:cat", "style:watercolor", "action:reading", "location:windowsill"]`

2. **KG Query:**
   - Recommendations: `mood:warm`, `lighting:natural`, `color_palette:pastel`
   - Example: "Cozy Cat Watercolor" prompt

3. **Prompt Generation:**
   - JSON: 14 dimensions assembled
   - Text: "a cat reading on windowsill, watercolor, warm mood, natural light..."

4. **ComfyUI Generation (Run 1):**
   - Output: `run-001_20260422_182000_0.png`
   - Score: 7.5 (below threshold)

5. **Evaluation Loop:**
   - Feedback: "lighting slightly dim, background lacks warmth"
   - Improved prompt: "...brighter natural window light, warm golden tones..."

6. **ComfyUI Generation (Run 2):**
   - Output: `run-002_20260422_182015_0.png`
   - Score: 8.3 (passes threshold)

7. **KG Update:**
   - Co-occurrence: `subject:cat` ↔ `style:watercolor` incremented
   - Prompt index: New entry added for "Cat Reading on Windowsill"

**Final Result:**
```json
{
  "status": "success",
  "runs": 2,
  "best_image": "~/image-gen-output/run-002_20260422_182015_0.png",
  "final_score": 8.3,
  "prompt": "a cat reading on windowsill, watercolor, warm mood, brighter natural light...",
  "kg_updated": true
}
```

---

## Configuration Reference

See `engine/config.json` for configurable parameters:

- `comfyui_host` / `comfyui_port`: ComfyUI server address
- `output_dir`: Image output directory
- `vision_model`: Multimodal evaluation model config
- `max_iterations`: Maximum refinement iterations (default: 3)
- `score_threshold`: Passing score threshold (default: 8)

---

## See Also

- `install-guide.md`: ComfyUI installation instructions
- `prompt-schema.md`: JSON Prompt 14-dimension schema details
- `engine/kg/engine.py`: KG engine API documentation