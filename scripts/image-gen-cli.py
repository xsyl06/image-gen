#!/usr/bin/env python3
"""Unified CLI for the image-gen pipeline.

Usage:
    python image-gen-cli.py <command> [options]

Commands:
    intent           Extract seed entities from text description
    skeleton         Get KG recommendations for seed entities
    assemble         Assemble JSON prompt from KG skeleton
    convert          Convert JSON prompt to positive/negative text
    validate         Validate JSON prompt against schema
    list-workflows   List available ComfyUI workflows
    inject           Inject prompts into a workflow
    generate         Submit workflow to ComfyUI and download images
    evaluate         Score a generated image against user intent
    describe         Analyze an image with the vision model
    compare          Compare two images with the vision model
    free-memory      Free ComfyUI VRAM
    update-kg        Record a successful generation in the KG
    check            Check ComfyUI connection status
    pipeline         Run the complete 6-step pipeline
"""

import argparse
import json
import sys
from pathlib import Path

# Add engine directory to path
ENGINE_DIR = Path(__file__).parent / "engine"
sys.path.insert(0, str(ENGINE_DIR))


# ── Helpers ─────────────────────────────────────────────────

def load_config(config_path=None):
    """Load configuration from file or default."""
    if config_path:
        config_file = Path(config_path)
    else:
        config_file = ENGINE_DIR / "config.json"
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    with open(config_file, "r") as f:
        cfg = json.load(f)
    if "output_dir" in cfg:
        cfg["output_dir"] = str(Path(cfg["output_dir"]).expanduser())
    return cfg


def output_json(data):
    """Write JSON to stdout for LLM consumption."""
    print(json.dumps(data, indent=2, ensure_ascii=False), file=sys.stdout)


def error(msg, code=1):
    """Write error to stderr and exit."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def read_stdin_json():
    """Parse JSON from stdin."""
    try:
        return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        error(f"Invalid JSON from stdin: {e}", 2)


def add_config_arg(parser):
    """Add --config argument to a parser."""
    parser.add_argument(
        "--config", "-c",
        help="Custom config file path (default: engine/config.json)"
    )


# ── Commands ────────────────────────────────────────────────

def cmd_intent(args):
    """Extract seed entities from text."""
    from intent import extract_seed_entities_llm
    cfg = load_config(args.config)
    seeds = extract_seed_entities_llm(args.text, cfg)
    output_json(seeds)


def cmd_skeleton(args):
    """Get KG recommendations."""
    from kg.engine import PromptKG
    if args.stdin:
        seeds = read_stdin_json()
    else:
        seeds = json.loads(args.seeds)
    kg = PromptKG()
    skeleton = kg.skeleton(seeds)
    output_json(skeleton)


def cmd_assemble(args):
    """Assemble JSON prompt from KG skeleton + seeds."""
    from prompt_assembly import assemble_json_prompt
    skeleton = json.loads(args.skeleton)
    seeds = json.loads(args.seeds) if args.seeds else None
    prompt = assemble_json_prompt(skeleton, args.intent, seeds=seeds)
    output_json(prompt)


def cmd_convert(args):
    """Convert JSON prompt to text."""
    from json_prompt import json_prompt_to_text, validate_json_prompt
    prompt = json.loads(args.prompt) if args.prompt else read_stdin_json()
    issues = validate_json_prompt(prompt)
    if issues:
        for issue in issues:
            print(f"Warning: {issue}", file=sys.stderr)
    result = json_prompt_to_text(prompt)
    output_json(result)


def cmd_validate(args):
    """Validate JSON prompt."""
    from json_prompt import validate_json_prompt
    prompt = json.loads(args.prompt) if args.prompt else read_stdin_json()
    issues = validate_json_prompt(prompt)
    output_json({"valid": len(issues) == 0, "issues": issues})


def cmd_list_workflows(args):
    """List available workflows."""
    from workflow_loader import list_workflows
    workflows = list_workflows()
    output_json(workflows)


def cmd_inject(args):
    """Inject prompts into workflow."""
    from workflow_loader import load_workflow, inject_prompts
    workflow = load_workflow(args.workflow)
    wf = inject_prompts(workflow, args.positive, args.negative)
    output_json(wf)


def cmd_generate(args):
    """Submit workflow to ComfyUI."""
    from comfyui import check_connection, generate_image
    cfg = load_config(args.config)
    from workflow_loader import load_workflow, inject_prompts
    try:
        workflow = load_workflow(args.workflow)
    except FileNotFoundError:
        error(f"Workflow not found: {args.workflow}")
    workflow = inject_prompts(workflow, args.positive, args.negative)
    if not check_connection(cfg):
        error(f"Cannot connect to ComfyUI at {cfg.get('comfyui_host')}:{cfg.get('comfyui_port')}")
    result = generate_image(workflow, cfg, filename_prefix=args.prefix or "cli-gen")
    output_json({"prompt_id": result["prompt_id"], "filepaths": result["filepaths"]})


def cmd_evaluate(args):
    """Evaluate a generated image."""
    from evaluator import evaluate_image
    cfg = load_config(args.config)
    result = evaluate_image(args.image, args.intent, cfg)
    output_json(result)


def cmd_describe(args):
    """Describe an image."""
    from comfyui import describe_image
    cfg = load_config(args.config)
    result = describe_image(args.image, args.prompt_text, cfg)
    output_json(result)


def cmd_compare(args):
    """Compare two images."""
    from comfyui import compare_images
    cfg = load_config(args.config)
    result = compare_images(args.image_a, args.image_b, args.prompt_text, cfg)
    output_json(result)


def cmd_free_memory(args):
    """Free ComfyUI VRAM."""
    from comfyui import free_memory
    cfg = load_config(args.config)
    ok = free_memory(cfg, unload_models=args.unload_models)
    output_json({"success": ok, "unload_models": args.unload_models})


def cmd_update_kg(args):
    """Record a successful generation in the KG."""
    from kg_update import update_kg
    entities = json.loads(args.entities)
    ok = update_kg(entities, args.positive_prompt, args.score, args.threshold)
    output_json({"updated": ok, "entities": entities, "score": args.score})


def cmd_check(args):
    """Check ComfyUI connection."""
    from comfyui import check_connection
    cfg = load_config(args.config)
    ok = check_connection(cfg)
    url = f"{cfg.get('comfyui_host')}:{cfg.get('comfyui_port')}"
    output_json({"connected": ok, "server": url})


def cmd_pipeline(args):
    """Run the complete 6-step pipeline."""
    cfg = load_config(args.config)

    # Step 1: Intent Recognition
    print("[1/6] Intent Recognition...", file=sys.stderr)
    from intent import extract_seed_entities_llm
    seeds = extract_seed_entities_llm(args.prompt, cfg)
    print(f"  Seeds: {json.dumps(seeds, ensure_ascii=False)}", file=sys.stderr)

    # Step 2: KG Query
    print("[2/6] KG Query...", file=sys.stderr)
    from kg.engine import PromptKG
    kg = PromptKG()
    skeleton = kg.skeleton(seeds)
    print(f"  Filled: {list(skeleton.get('filled', {}).keys())}", file=sys.stderr)

    # Step 3: Prompt Assembly
    print("[3/6] Prompt Assembly...", file=sys.stderr)
    from prompt_assembly import assemble_json_prompt
    json_prompt = assemble_json_prompt(skeleton, args.prompt, seeds=seeds)
    text_result = _to_text(json_prompt)
    positive = text_result["positive"]
    negative = text_result["negative"]
    print(f"  Positive: {positive[:120]}...", file=sys.stderr)

    # Step 4: ComfyUI Generation
    print("[4/6] ComfyUI Generation...", file=sys.stderr)
    from comfyui import check_connection, generate_image, free_memory
    from workflow_loader import load_workflow, inject_prompts

    if not check_connection(cfg):
        error(f"Cannot connect to ComfyUI at {cfg.get('comfyui_host')}:{cfg.get('comfyui_port')}")

    workflow_name = cfg.get("default_workflow", "workflows/ernie_image_gguf.json")
    try:
        base_workflow = load_workflow(workflow_name)
    except FileNotFoundError:
        error(f"Workflow not found: {workflow_name}")

    max_iterations = cfg.get("max_iterations", 3)
    score_threshold = cfg.get("score_threshold", 8)
    if args.iterations:
        max_iterations = args.iterations
    if args.threshold:
        score_threshold = args.threshold

    best_run = None
    current_prompt = json_prompt.copy()

    for i in range(1, max_iterations + 1):
        print(f"\n  --- Iteration {i}/{max_iterations} ---", file=sys.stderr)

        text_result = _to_text(current_prompt)
        positive = text_result["positive"]
        negative = text_result["negative"]

        workflow = inject_prompts(base_workflow, positive, negative)
        try:
            result = generate_image(
                workflow, cfg,
                filename_prefix=f"pipeline-{i:03d}",
                prompt=args.prompt
            )
        except Exception as e:
            print(f"  Generation failed: {e}", file=sys.stderr)
            break

        image_path = result.get("filepaths", [None])[0]
        if not image_path:
            print(f"  No image output", file=sys.stderr)
            break

        print(f"  Image: {image_path}", file=sys.stderr)

        # Step 5: Evaluate
        print(f"  Evaluating...", file=sys.stderr)
        from evaluator import evaluate_image
        evaluation = evaluate_image(image_path, args.prompt, cfg)
        score = evaluation.get("weighted_score", 0)
        print(f"  Score: {score}/{score_threshold}", file=sys.stderr)

        best_run = {
            "run": i,
            "image": image_path,
            "score": score,
            "evaluation": evaluation,
            "positive_prompt": positive,
        }

        if score >= score_threshold:
            print(f"  Passed threshold! Stopping.", file=sys.stderr)
            break

        improved_text = evaluation.get("improved_prompt", "")
        if improved_text:
            print(f"  Refining prompt for next iteration...", file=sys.stderr)
            current_prompt["subject"] = improved_text
        else:
            print(f"  No improvement suggested, stopping.", file=sys.stderr)
            break

        if i < max_iterations:
            free_memory(cfg, unload_models=True)

    if not best_run:
        error("Pipeline failed — no successful generation")

    # Step 6: KG Update
    print("\n[6/6] KG Update...", file=sys.stderr)
    if best_run["score"] >= score_threshold:
        from kg_update import update_kg
        used_entities = [s for s in seeds if ":" in s]
        if not used_entities:
            for field in ["subject", "style", "mood", "genre"]:
                if field in json_prompt and isinstance(json_prompt[field], str):
                    used_entities.append(f"{field}:{json_prompt[field]}")
        updated = update_kg(used_entities, best_run["positive_prompt"], best_run["score"], score_threshold)
        print(f"  {'Updated' if updated else 'Skipped (already exists)'}", file=sys.stderr)
    else:
        print(f"  Skipped — score {best_run['score']} below threshold {score_threshold}", file=sys.stderr)

    # Output final result
    output_json(best_run)


def _to_text(prompt_json):
    """Convert JSON prompt to text without import cycle."""
    from json_prompt import json_prompt_to_text
    return json_prompt_to_text(prompt_json)


# ── Argument Parser ─────────────────────────────────────────

def build_parser():
    parser = argparse.ArgumentParser(
        description="Unified CLI for the image-gen pipeline"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # intent
    p = subparsers.add_parser("intent", help="Extract seed entities from text")
    p.add_argument("--text", "-t", required=True, help="User description")
    add_config_arg(p)
    p.set_defaults(func=cmd_intent)

    # skeleton
    p = subparsers.add_parser("skeleton", help="Get KG recommendations")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--seeds", "-s", help='JSON array of seed entity tags')
    g.add_argument("--stdin", action="store_true", help="Read seeds from stdin")
    p.set_defaults(func=cmd_skeleton)

    # assemble
    p = subparsers.add_parser("assemble", help="Assemble JSON prompt")
    p.add_argument("--skeleton", required=True, help="KG skeleton JSON")
    p.add_argument("--seeds", help='JSON array of seed entity tags')
    p.add_argument("--intent", required=True, help="User description")
    p.set_defaults(func=cmd_assemble)

    # convert
    p = subparsers.add_parser("convert", help="Convert JSON prompt to text")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--prompt", help="JSON prompt string")
    g.add_argument("--stdin", action="store_true", help="Read from stdin")
    p.set_defaults(func=cmd_convert)

    # validate
    p = subparsers.add_parser("validate", help="Validate JSON prompt")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--prompt", help="JSON prompt string")
    g.add_argument("--stdin", action="store_true", help="Read from stdin")
    p.set_defaults(func=cmd_validate)

    # list-workflows
    p = subparsers.add_parser("list-workflows", help="List available workflows")
    p.set_defaults(func=cmd_list_workflows)

    # inject
    p = subparsers.add_parser("inject", help="Inject prompts into workflow")
    p.add_argument("--workflow", required=True, help="Workflow name or path")
    p.add_argument("--positive", required=True, help="Positive prompt")
    p.add_argument("--negative", default=None, help="Negative prompt")
    p.set_defaults(func=cmd_inject)

    # generate
    p = subparsers.add_parser("generate", help="Submit workflow to ComfyUI")
    p.add_argument("--workflow", required=True, help="Workflow name or path")
    p.add_argument("--positive", required=True, help="Positive prompt")
    p.add_argument("--negative", default=None, help="Negative prompt")
    p.add_argument("--prefix", help="Output filename prefix")
    add_config_arg(p)
    p.set_defaults(func=cmd_generate)

    # evaluate
    p = subparsers.add_parser("evaluate", help="Evaluate a generated image")
    p.add_argument("--image", required=True, help="Path to image file")
    p.add_argument("--intent", required=True, help="Original user description")
    add_config_arg(p)
    p.set_defaults(func=cmd_evaluate)

    # describe
    p = subparsers.add_parser("describe", help="Describe an image")
    p.add_argument("--image", required=True, help="Path to image file")
    p.add_argument("--prompt", dest="prompt_text", required=True, help="Prompt for vision model")
    add_config_arg(p)
    p.set_defaults(func=cmd_describe)

    # compare
    p = subparsers.add_parser("compare", help="Compare two images")
    p.add_argument("--image-a", required=True, help="Path to first image")
    p.add_argument("--image-b", required=True, help="Path to second image")
    p.add_argument("--prompt", dest="prompt_text", required=True, help="Prompt for vision model")
    add_config_arg(p)
    p.set_defaults(func=cmd_compare)

    # free-memory
    p = subparsers.add_parser("free-memory", help="Free ComfyUI VRAM")
    p.add_argument("--unload", dest="unload_models", action="store_true",
                   help="Fully unload models (slower but cleanest)")
    add_config_arg(p)
    p.set_defaults(func=cmd_free_memory)

    # update-kg
    p = subparsers.add_parser("update-kg", help="Record a generation in the KG")
    p.add_argument("--entities", required=True, help='JSON array of entity tags')
    p.add_argument("--positive-prompt", required=True, help="The positive prompt text")
    p.add_argument("--score", type=float, required=True, help="Evaluation weighted score")
    p.add_argument("--threshold", type=float, default=8, help="Minimum score to record")
    p.set_defaults(func=cmd_update_kg)

    # check
    p = subparsers.add_parser("check", help="Check ComfyUI connection")
    add_config_arg(p)
    p.set_defaults(func=cmd_check)

    # pipeline
    p = subparsers.add_parser("pipeline", help="Run complete 6-step pipeline")
    p.add_argument("--prompt", "-p", required=True, help="User description")
    p.add_argument("--iterations", "-i", type=int, help="Max iterations (default: 3)")
    p.add_argument("--threshold", "-t", type=int, help="Score threshold (default: 8)")
    add_config_arg(p)
    p.set_defaults(func=cmd_pipeline)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        args.func(args)
    except Exception as e:
        error(f"{args.command}: {e}")


if __name__ == "__main__":
    main()
