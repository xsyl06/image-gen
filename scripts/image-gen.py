#!/usr/bin/env python3
"""CLI entry point for image-gen skill.

Usage:
    python image-gen.py "a cat reading a book"
    python image-gen.py "a cat" --iterations 5
    python image-gen.py "a cat" --threshold 9
    python image-gen.py "a cat" --config custom.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add engine directory to path
ENGINE_DIR = Path(__file__).parent.parent / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from kg.engine import PromptKG
from json_prompt import json_prompt_to_text
from comfyui import check_connection, generate_image, free_memory
from intent import extract_seed_entities_llm
from workflow_loader import load_workflow, inject_prompts
from evaluator import evaluate_image
from kg_update import update_kg


def load_config(config_path=None):
    """Load configuration from file or default."""
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = ENGINE_DIR / "config.json"

    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)

    with open(config_file, "r") as f:
        cfg = json.load(f)

    # Expand output_dir path
    if "output_dir" in cfg:
        cfg["output_dir"] = Path(cfg["output_dir"]).expanduser()

    return cfg


def _detect_confrontation(json_prompt, user_intent):
    """Detect left-vs-right or top-vs-bottom comparison intent from user description."""
    lower = user_intent.lower()

    # Detect comparison keywords
    is_comparison = any(kw in lower for kw in [
        "left vs right", "left_vs_right", "对比", "对比图",
        "comparison image", "compare", " versus ", "对照",
    ])

    if not is_comparison:
        return

    # Determine layout
    layout = "left_vs_right"
    if any(kw in lower for kw in ["top vs", "top_vs", "above vs", "上下", "上下对比"]):
        layout = "top_vs_bottom"

    import re
    if layout == "left_vs_right":
        # Prefer explicit "X on the left, Y on the right" pattern
        lr_pattern = r'([^,]+?)\s+on\s+the\s+left[^,]*,\s*([^,]+?)\s+on\s+the\s+right'
        lr_match = re.search(lr_pattern, lower)

        if lr_match:
            left_desc = lr_match.group(1).strip()
            right_desc = lr_match.group(2).strip()
        else:
            # Fallback: split by "vs" and use first meaningful segment
            for sep in [" vs ", " versus "]:
                if sep in lower:
                    parts = lower.split(sep)
                    if len(parts) == 2:
                        left_desc = parts[0].strip()
                        right_desc = parts[1].strip()
                    break
            else:
                left_desc = "left side"
                right_desc = "right side"

        json_prompt["confrontation"] = {
            "layout": "left_vs_right",
            "left": {"name": "left", "details": left_desc},
            "right": {"name": "right", "details": right_desc},
        }
    else:
        json_prompt["confrontation"] = {
            "layout": "top_vs_bottom",
            "top": {"name": "top", "details": "top half"},
            "bottom": {"name": "bottom", "details": "bottom half"},
        }


def assemble_json_prompt(skeleton, user_intent, seeds=None):
    """Assemble JSON prompt from skeleton recommendations + raw LLM seeds.

    Args:
        skeleton: KG skeleton dict with filled/recommendations
        user_intent: Original user description (fallback for unknown entities)
        seeds: Original LLM-extracted entity tags (to preserve unknown KG tags)

    Strategy:
    1. Fill categories from KG skeleton (known entities)
    2. For categories where LLM found entities but KG doesn't know them,
       use the LLM-extracted value directly (not just user_intent fallback)
    3. Fill remaining categories from KG recommendations
    4. Use user_intent as subject fallback only if no entity found at all
    """
    json_prompt = {}

    field_map = {
        "subject": "subject",
        "style": "style",
        "mood": "mood",
        "composition": "composition",
        "lighting": "lighting",
        "background": "background",
        "color_palette": "color_palette",
        "genre": "genre",
    }

    # Track which categories have been filled (by KG or LLM)
    filled_cats = set()

    # 1. Fill from KG skeleton.filled (known entities)
    for category, entity_info in skeleton.get("filled", {}).items():
        entity_tag = entity_info.get("entity", "")
        value = entity_tag.split(":")[-1] if ":" in entity_tag else entity_tag
        field = field_map.get(category, category)
        json_prompt[field] = value
        filled_cats.add(category)

    # 2. Fill from raw LLM seeds for categories KG didn't recognize
    #    This preserves user intent that falls outside the KG
    if seeds:
        for seed in seeds:
            if ":" in seed:
                cat, value = seed.split(":", 1)
                field = field_map.get(cat, cat)
                # Only fill if KG didn't already fill this category
                if cat not in filled_cats and field not in json_prompt:
                    json_prompt[field] = value
                    filled_cats.add(cat)

    # 3. Fill remaining categories from KG recommendations
    for category, recs in skeleton.get("recommendations", {}).items():
        if recs and category not in filled_cats:
            top_rec = recs[0]
            entity_tag = top_rec.get("entity", "")
            value = entity_tag.split(":")[-1] if ":" in entity_tag else entity_tag
            field = field_map.get(category, category)
            json_prompt[field] = value
            filled_cats.add(category)

    # 4. Fallback: use user intent as subject if nothing found
    if "subject" not in json_prompt:
        json_prompt["subject"] = user_intent

    # Detect confrontation/comparison intent from user description
    _detect_confrontation(json_prompt, user_intent)

    # Default negative constraints
    json_prompt["negative_constraints"] = [
        "blurry",
        "distorted",
        "ugly",
        "watermark",
        "low quality"
    ]

    return json_prompt


def run_generation(user_intent, cfg, kg):
    """Run the generation pipeline."""
    print(f"\n=== Image Generation Pipeline ===")
    print(f"User intent: {user_intent}")
    print(f"Config: {cfg.get('comfyui_host')}:{cfg.get('comfyui_port')}")

    # Step 1: Extract seed entities (LLM-based)
    print(f"\n[Step 1] Intent Recognition (LLM)")
    seeds = extract_seed_entities_llm(user_intent, cfg)
    print(f"  Seeds: {seeds}")

    # Step 2: KG Query
    print(f"\n[Step 2] KG Query")
    skeleton = kg.skeleton(seeds)
    print(f"  Filled: {list(skeleton.get('filled', {}).keys())}")
    print(f"  Recommendations: {list(skeleton.get('recommendations', {}).keys())}")

    # Step 3: Prompt Generation
    print(f"\n[Step 3] Prompt Generation")
    json_prompt = assemble_json_prompt(skeleton, user_intent, seeds=seeds)
    text_result = json_prompt_to_text(json_prompt)

    positive = text_result.get("positive", "")
    negative = text_result.get("negative", "")

    print(f"  JSON prompt: {json.dumps(json_prompt, indent=2)}")
    print(f"  Positive: {positive[:100]}...")
    print(f"  Negative: {negative}")

    # Step 4: ComfyUI Generation
    print(f"\n[Step 4] ComfyUI Generation")

    # Check connection
    if not check_connection(cfg):
        print(f"  ERROR: Cannot connect to ComfyUI at {cfg.get('comfyui_host')}:{cfg.get('comfyui_port')}")
        print(f"  Please start ComfyUI: python main.py --port {cfg.get('comfyui_port')}")
        return None

    print(f"  Connection OK")

    # Load default workflow from config
    workflow_name = cfg.get("default_workflow", "workflows/ernie_image_gguf.json")
    try:
        base_workflow = load_workflow(workflow_name)
        print(f"  Loaded workflow: {workflow_name}")
    except FileNotFoundError as e:
        print(f"  WARNING: {e}")
        print(f"  Using empty workflow (generation may fail)")
        base_workflow = {"prompt": positive, "negative_prompt": negative}

    max_iterations = cfg.get("max_iterations", 3)
    score_threshold = cfg.get("score_threshold", 8)

    # Steps 4-6: Generation + Evaluation Loop + KG Update
    best_run = None
    current_prompt = json_prompt.copy()

    for i in range(1, max_iterations + 1):
        print(f"\n--- Iteration {i}/{max_iterations} ---")

        # Convert to text
        text_result = json_prompt_to_text(current_prompt)
        positive = text_result.get("positive", "")
        negative = text_result.get("negative", "")

        print(f"  Positive: {positive[:120]}...")
        print(f"  Negative: {negative}")

        # Step 4: Inject and generate
        workflow = inject_prompts(base_workflow, positive, negative)
        try:
            result = generate_image(
                workflow, cfg,
                filename_prefix=f"cli-run-{i:03d}",
                prompt=user_intent
            )
        except Exception as e:
            print(f"  ERROR: Generation failed: {e}")
            break

        image_path = result.get("filepaths", [None])[0]
        if not image_path:
            print(f"  ERROR: No image output")
            break

        print(f"  Image: {image_path}")

        # Step 5: Evaluate
        print(f"  Evaluating...")
        evaluation = evaluate_image(image_path, user_intent, cfg)
        score = evaluation.get("weighted_score", 0)
        print(f"  Score: {score}/{score_threshold}")
        strengths = evaluation.get("strengths", [])
        weaknesses = evaluation.get("weaknesses", [])
        if strengths:
            print(f"  Strengths: {', '.join(strengths)}")
        if weaknesses:
            print(f"  Weaknesses: {', '.join(weaknesses)}")

        best_run = {
            "run": i,
            "image": image_path,
            "score": score,
            "evaluation": evaluation,
        }

        # Check threshold
        if score >= score_threshold:
            print(f"  Passed threshold! Stopping.")
            break

        # Improve prompt based on feedback
        improved_text = evaluation.get("improved_prompt", "")
        if improved_text:
            print(f"  Refining prompt for next iteration...")
            current_prompt["subject"] = improved_text
        else:
            print(f"  No improvement suggested, stopping.")
            break

        # Free memory between runs
        if i < max_iterations:
            free_memory(cfg, unload_models=True)

    # Step 6: KG Update
    if best_run and best_run["score"] >= score_threshold:
        print(f"\n[Step 6] KG Update")
        used_entities = [s for s in seeds if ":" in s]
        if not used_entities:
            # Extract from json_prompt fields
            for field in ["subject", "style", "mood", "genre"]:
                if field in json_prompt and isinstance(json_prompt[field], str):
                    used_entities.append(f"{field}:{json_prompt[field]}")
        updated = update_kg(used_entities, best_run.get("image", ""), best_run["score"], score_threshold)
        if updated:
            print(f"  KG updated with successful combination")
        else:
            print(f"  KG not updated (combination already exists)")

    return best_run


def main():
    parser = argparse.ArgumentParser(
        description="Image generation CLI tool using KG + ComfyUI pipeline"
    )

    parser.add_argument(
        "prompt",
        help="User intent / image description"
    )

    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=3,
        help="Maximum evaluation iterations (default: 3)"
    )

    parser.add_argument(
        "--threshold", "-t",
        type=int,
        default=8,
        help="Quality score threshold (default: 8, scale 1-10)"
    )

    parser.add_argument(
        "--config", "-c",
        help="Custom config file path (default: engine/config.json)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Load configuration
    cfg = load_config(args.config)

    # Override config with CLI arguments
    cfg["max_iterations"] = args.iterations
    cfg["score_threshold"] = args.threshold

    # Initialize KG
    print("Initializing PromptKG...")
    kg = PromptKG()
    print(f"  Entities: {len(kg.entities)}")
    print(f"  Categories: {kg.categories}")

    # Run generation
    result = run_generation(args.prompt, cfg, kg)

    if result and result.get("image"):
        print(f"\n=== SUCCESS ===")
        print(f"Best image (score {result['score']}/{score_threshold}):")
        print(f"  - {result['image']}")
        return 0
    else:
        print(f"\n=== FAILED ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())