"""Evaluation Loop — score generated images and refine prompts iteratively.

Uses the configured vision model to evaluate images against user intent
on 6 dimensions, then suggests prompt improvements if the score is below
threshold.
"""

import json
import re
import sys

from comfyui import describe_image, free_memory
from workflow_loader import inject_prompts


# ── Evaluation Prompt ─────────────────────────────────────

EVALUATION_PROMPT = """Evaluate this generated image against the user's original request:
"{user_intent}"

Score each dimension from 1 to 10:
1. Subject Accuracy: Does the image match the described subject?
2. Style Fidelity: Is the artistic style correctly rendered?
3. Mood/Atmosphere: Does it convey the intended mood?
4. Composition Quality: Is the layout well-structured?
5. Technical Quality: Resolution, clarity, detail level
6. Overall Satisfaction: General aesthetic appeal

Also provide:
- strengths: List of 2-3 things that work well
- weaknesses: List of 2-3 issues to fix
- improved_prompt: Specific prompt text that would address the weaknesses

Return as JSON with these exact keys:
subject_accuracy, style_fidelity, mood_atmosphere, composition_quality, technical_quality, overall_satisfaction, strengths, weaknesses, improved_prompt, weighted_score

Calculate weighted_score as:
subject_accuracy * 0.25 + style_fidelity * 0.20 + mood_atmosphere * 0.15 + composition_quality * 0.15 + technical_quality * 0.15 + overall_satisfaction * 0.10
"""


def parse_evaluation_response(text):
    """Parse the vision model's evaluation response into a structured dict."""
    text = re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE).strip()

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            result = json.loads(json_match.group())

            # Calculate weighted score if not provided
            if "weighted_score" not in result:
                weights = {
                    "subject_accuracy": 0.25,
                    "style_fidelity": 0.20,
                    "mood_atmosphere": 0.15,
                    "composition_quality": 0.15,
                    "technical_quality": 0.15,
                    "overall_satisfaction": 0.10,
                }
                score = sum(
                    result.get(k, 5) * v for k, v in weights.items()
                )
                result["weighted_score"] = round(score, 2)

            return result
        except json.JSONDecodeError:
            pass

    # Fallback: return default scores
    return {
        "subject_accuracy": 5,
        "style_fidelity": 5,
        "mood_atmosphere": 5,
        "composition_quality": 5,
        "technical_quality": 5,
        "overall_satisfaction": 5,
        "weighted_score": 5.0,
        "strengths": ["manual evaluation required"],
        "weaknesses": ["unable to parse evaluation response"],
        "improved_prompt": "",
    }


def evaluate_image(image_path, user_intent, cfg):
    """Evaluate a generated image using the vision model.

    Args:
        image_path: Path to the generated image
        user_intent: Original user description
        cfg: Config dict with vision_model settings

    Returns:
        Dict with scores, strengths, weaknesses, improved_prompt, weighted_score
    """
    prompt = EVALUATION_PROMPT.format(user_intent=user_intent)

    try:
        result = describe_image(image_path, prompt, cfg)
    except Exception as e:
        print(f"Warning: Vision evaluation failed: {e}", file=sys.stderr)
        return {
            "subject_accuracy": None,
            "style_fidelity": None,
            "mood_atmosphere": None,
            "composition_quality": None,
            "technical_quality": None,
            "overall_satisfaction": None,
            "weighted_score": None,
            "strengths": ["evaluation API unreachable — manual review recommended"],
            "weaknesses": [],
            "improved_prompt": "",
            "_skip_auto_refinement": True,
        }

    # describe_image returns a dict that may have:
    # 1. Top-level score keys directly (when comfyui_metadata is present)
    # 2. A "description" field containing text to parse
    if isinstance(result, dict):
        # Case 1: Vision API returned structured JSON directly as top-level keys
        if "subject_accuracy" in result and "weighted_score" in result:
            return {
                "subject_accuracy": result.get("subject_accuracy", 5),
                "style_fidelity": result.get("style_fidelity", 5),
                "mood_atmosphere": result.get("mood_atmosphere", 5),
                "composition_quality": result.get("composition_quality", 5),
                "technical_quality": result.get("technical_quality", 5),
                "overall_satisfaction": result.get("overall_satisfaction", 5),
                "weighted_score": result.get("weighted_score", 5.0),
                "strengths": result.get("strengths", []),
                "weaknesses": result.get("weaknesses", []),
                "improved_prompt": result.get("improved_prompt", ""),
            }
        # Case 2: Response text in "description" field
        response_text = result.get("description", "")
        if not response_text:
            for v in result.values():
                if isinstance(v, str) and len(v) > 20:
                    response_text = v
                    break
        if response_text:
            return parse_evaluation_response(response_text)

    return {
        "subject_accuracy": 5,
        "style_fidelity": 5,
        "mood_atmosphere": 5,
        "composition_quality": 5,
        "technical_quality": 5,
        "overall_satisfaction": 5,
        "weighted_score": 5.0,
        "strengths": ["manual evaluation required"],
        "weaknesses": ["unexpected evaluation response format"],
        "improved_prompt": "",
    }


def run_evaluation_loop(user_intent, json_prompt, workflow, cfg, generate_fn=None):
    """Full evaluation loop: generate → evaluate → refine → repeat.

    Args:
        user_intent: Original user description
        json_prompt: Assembled JSON prompt
        workflow: ComfyUI workflow dict
        cfg: Config dict
        generate_fn: Optional custom generate function (for testing).
                     Defaults to comfyui.generate_image

    Returns:
        List of run dicts with image, evaluation, prompt for each iteration
    """
    if generate_fn is None:
        from comfyui import generate_image

    from json_prompt import json_prompt_to_text

    max_iterations = cfg.get("max_iterations", 3)
    score_threshold = cfg.get("score_threshold", 8)

    runs = []
    current_prompt = json_prompt.copy()

    for i in range(1, max_iterations + 1):
        print(f"\n--- Iteration {i}/{max_iterations} ---", file=sys.stderr)

        # Convert to text
        text_result = json_prompt_to_text(current_prompt)
        positive = text_result["positive"]
        negative = text_result["negative"]

        # Inject into workflow
        current_workflow = inject_prompts(workflow, positive, negative)

        # Generate
        try:
            result = generate_fn(current_workflow, cfg, filename_prefix=f"run-{i:03d}")
        except Exception as e:
            print(f"Generation failed in iteration {i}: {e}", file=sys.stderr)
            runs.append({"run": i, "error": str(e)})
            break

        image_path = result.get("filepaths", [None])[0]
        if not image_path:
            print(f"No image output in iteration {i}", file=sys.stderr)
            break

        # Free memory between runs
        if i < max_iterations:
            free_memory(cfg, unload_models=False)

        # Evaluate
        evaluation = evaluate_image(image_path, user_intent, cfg)

        runs.append({
            "run": i,
            "image": image_path,
            "positive_prompt": positive,
            "evaluation": evaluation,
        })

        print(f"Score: {evaluation['weighted_score']}/{score_threshold}", file=sys.stderr)

        # Check threshold
        score = evaluation.get("weighted_score")
        if score is not None and score >= score_threshold:
            print(f"Passed threshold! Stopping iteration.", file=sys.stderr)
            break

        # Improve prompt
        if evaluation.get("_skip_auto_refinement"):
            print(f"Evaluation unavailable, stopping refinement.", file=sys.stderr)
            break

        improved_text = evaluation.get("improved_prompt", "")
        if improved_text:
            print(f"Improving prompt for next iteration...", file=sys.stderr)
            current_prompt = _refine_prompt(current_prompt, improved_text)
        else:
            print(f"No improvement suggested, stopping.", file=sys.stderr)
            break

    return runs



def _refine_prompt(json_prompt, improved_text):
    """Incorporate improved text into the JSON prompt.

    Appends the improved text as subject details to preserve existing
    structured fields (style, mood, composition, etc.).
    """
    refined = json_prompt.copy()

    subject = refined.get("subject", "")
    if isinstance(subject, dict):
        existing = subject.get("details", "")
        subject["details"] = f"{existing}\n{improved_text}".strip() if existing else improved_text
    else:
        refined["subject"] = {"main": subject, "details": improved_text}

    # Preserve negative constraints
    if "negative_constraints" not in refined:
        refined["negative_constraints"] = [
            "blurry", "distorted", "ugly", "watermark", "low quality"
        ]

    return refined
