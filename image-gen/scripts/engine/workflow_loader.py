"""Workflow loader — load and validate ComfyUI API workflow JSON files.

ComfyUI workflows are exported from the browser interface via
the gear icon → "Save (API format)". They are placed in
engine/workflows/ and loaded by name.
"""

import copy
import json
import random
from pathlib import Path

WORKFLOWS_DIR = Path(__file__).parent / "workflows"


def load_workflow(name_or_path, engine_root=None):
    """Load a ComfyUI API workflow JSON file.

    Args:
        name_or_path: Either a filename (e.g. "my_workflow.json") or a full path.
                      If just a name, looks in engine/workflows/.
        engine_root: Optional override for the engine root directory.

    Returns:
        Dict of the workflow JSON (nodes keyed by ID).

    Raises:
        FileNotFoundError: If the workflow file doesn't exist.
        ValueError: If the JSON is invalid.
    """
    path = Path(name_or_path)

    # If it's just a filename (no directory), look in workflows/
    if not path.is_absolute() and len(path.parts) == 1:
        path = WORKFLOWS_DIR / path
    # If it starts with "workflows/", resolve relative to WORKFLOWS_DIR
    elif not path.is_absolute() and path.parts[0] == "workflows":
        path = WORKFLOWS_DIR / Path(*path.parts[1:])

    # If no extension, add .json
    if path.suffix != ".json":
        path = path.with_suffix(".json")

    if not path.exists():
        raise FileNotFoundError(f"Workflow not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            workflow = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in workflow {path}: {e}") from None

    return workflow


def list_workflows():
    """List all available workflow JSON files."""
    if not WORKFLOWS_DIR.exists():
        return []
    return sorted([
        f.name for f in WORKFLOWS_DIR.iterdir()
        if f.suffix == ".json"
    ])


DEFAULT_NEGATIVE = "blurry, distorted, ugly, watermark, low quality, deformed, bad anatomy,underexposed, grainy shadows, loss of detail in dark areas,deformed face, extra eyes, fused fingers,Misplaced Chinese characters, mixed use of traditional characters, pinyin notation, and character overlapping"


def inject_prompts(workflow, positive, negative=None):
    """Inject positive and negative prompts into a ComfyUI workflow.

    Strategy:
    1. Find CLIPTextEncode nodes — first = positive, second = negative
    2. If no second CLIPTextEncode found, trace KSampler negative input
       to its source node and replace accordingly
    3. If negative is empty/unset, use DEFAULT_NEGATIVE

    Args:
        workflow: Workflow dict from load_workflow()
        positive: Positive prompt text
        negative: Negative prompt text (optional, defaults to DEFAULT_NEGATIVE)

    Returns:
        Modified workflow dict (deep copy, original unchanged)
    """
    wf = copy.deepcopy(workflow)

    if not negative:
        negative = DEFAULT_NEGATIVE

    positive_injected = False
    negative_injected = False

    # Phase 1: Inject into CLIPTextEncode nodes
    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "CLIPTextEncode":
            inputs = node.get("inputs", {})
            if not positive_injected:
                inputs["text"] = positive
                positive_injected = True
            elif not negative_injected:
                inputs["text"] = negative
                negative_injected = True

    # Phase 2: If negative not injected, trace KSampler negative inputs
    if not negative_injected:
        for _, node in wf.items():
            if not isinstance(node, dict):
                continue
            ct = node.get("class_type", "")
            if ct in ("KSampler", "KSamplerAdvanced", "SamplerCustomAdvanced"):
                neg_input = node.get("inputs", {}).get("negative")
                if neg_input and isinstance(neg_input, list):
                    source_node_id = str(neg_input[0])
                    _inject_negative_to_node(wf, source_node_id, negative)
                    negative_injected = True
                    break

        # Phase 3: Last resort — set negative on all CLIPTextEncode nodes
        # that already have the positive prompt (they might be used for both)
        if not negative_injected:
            for _, node in wf.items():
                if node.get("class_type") == "CLIPTextEncode":
                    inputs = node.get("inputs", {})
                    if inputs.get("text") == positive:
                        # This node was set as positive, leave it
                        pass
                    else:
                        inputs["text"] = negative
                        negative_injected = True

    # Phase 4: Randomize seed for KSampler nodes
    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        if ct in ("KSampler", "KSamplerAdvanced", "SamplerCustomAdvanced"):
            inputs = node.get("inputs", {})
            if "seed" in inputs:
                inputs["seed"] = random.randint(1, 999999999999999)

    return wf


def inject_dimensions(workflow, width=None, height=None):
    """Inject image dimensions into a ComfyUI workflow.

    Handles two node patterns:
    1. PrimitiveInt nodes with _meta.title "Width"/"Height" (ernie_image workflow)
    2. EmptyLatentImage / EmptyFlux2LatentImage / EmptySD3LatentImage with direct inputs

    Args:
        workflow: Workflow dict from load_workflow()
        width: Desired image width in pixels (None = keep default)
        height: Desired image height in pixels (None = keep default)

    Returns:
        Modified workflow dict (deep copy, original unchanged)
    """
    if width is None and height is None:
        return copy.deepcopy(workflow)

    wf = copy.deepcopy(workflow)

    # Phase 1: Try PrimitiveInt nodes (title-based matching)
    width_set = width is None
    height_set = height is None

    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != "PrimitiveInt":
            continue
        title = node.get("_meta", {}).get("title", "").lower()
        if not width_set and "width" in title:
            node["inputs"]["value"] = width
            width_set = True
        elif not height_set and "height" in title:
            node["inputs"]["value"] = height
            height_set = True

    if width_set and height_set:
        return wf

    # Phase 2: Try EmptyLatentImage nodes with direct width/height inputs
    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        ct = node.get("class_type", "")
        if "LatentImage" not in ct:
            continue
        inputs = node.get("inputs", {})
        if not width_set and "width" in inputs and not isinstance(inputs["width"], list):
            inputs["width"] = width
            width_set = True
        if not height_set and "height" in inputs and not isinstance(inputs["height"], list):
            inputs["height"] = height
            height_set = True

    return wf


def _inject_negative_to_node(wf, node_id, negative):
    """Inject negative prompt into a specific node by ID.

    Handles CLIPTextEncode (replace text) and ConditioningZeroOut
    (skip — zero-out nodes don't need prompt text).
    """
    target = wf.get(node_id)
    if not target or not isinstance(target, dict):
        return
    ct = target.get("class_type", "")
    if ct == "CLIPTextEncode":
        target.get("inputs", {})["text"] = negative
    # ConditioningZeroOut / other conditioning nodes: no text to replace
