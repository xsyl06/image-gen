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
ENGINE_DIR = Path(__file__).parent / "engine"
print(str(ENGINE_DIR))
sys.path.insert(0, str(ENGINE_DIR))

from kg.engine import PromptKG
from json_prompt import json_prompt_to_text
from comfyui import check_connection, generate_image, free_memory
from intent import extract_seed_entities_llm
from workflow_loader import load_workflow, inject_prompts
from evaluator import evaluate_image
from kg_update import update_kg
from prompt_assembly import assemble_json_prompt


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
        score = evaluation.get("weighted_score")
        skip_refinement = evaluation.get("_skip_auto_refinement", False)
        if score is not None:
            print(f"  Score: {score}/{score_threshold}")
        else:
            print(f"  Score: N/A (evaluation unavailable)")
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

        # Check threshold (skip if score unavailable)
        if score is not None and score >= score_threshold:
            print(f"  Passed threshold! Stopping.")
            break

        # Improve prompt based on feedback
        if skip_refinement:
            print(f"  Evaluation unavailable, stopping refinement.")
            break

        improved_text = evaluation.get("improved_prompt", "")
        if improved_text:
            print(f"  Refining prompt for next iteration...")
            # Append improved text as details rather than overwriting the entire subject
            subject = current_prompt.get("subject", "")
            if isinstance(subject, dict):
                existing = subject.get("details", "")
                subject["details"] = f"{existing}\n{improved_text}".strip() if existing else improved_text
            else:
                current_prompt["subject"] = {"main": subject, "details": improved_text}
        else:
            print(f"  No improvement suggested, stopping.")
            break

        # Free memory between runs
        if i < max_iterations:
            free_memory(cfg, unload_models=True)

    # Step 6: KG Update
    if best_run and best_run["score"] is not None and best_run["score"] >= score_threshold:
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
        print(f"Best image (score {result['score']}/{cfg['score_threshold']}):")
        print(f"  - {result['image']}")
        return 0
    else:
        print(f"\n=== FAILED ===")
        return 1


if __name__ == "__main__":
    sys.exit(main())