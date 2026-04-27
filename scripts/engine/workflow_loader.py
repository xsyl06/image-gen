"""Workflow loader — load and validate ComfyUI API workflow JSON files.

ComfyUI workflows are exported from the browser interface via
the gear icon → "Save (API format)". They are placed in
engine/workflows/ and loaded by name.
"""

import json
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


def inject_prompts(workflow, positive, negative=None):
    """Inject positive and negative prompts into a ComfyUI workflow.

    Finds CLIPTextEncode nodes and replaces their text inputs.
    First one found = positive, second one = negative.

    Args:
        workflow: Workflow dict from load_workflow()
        positive: Positive prompt text
        negative: Negative prompt text (optional)

    Returns:
        Modified workflow dict (deep copy, original unchanged)
    """
    import copy
    wf = copy.deepcopy(workflow)

    positive_injected = False
    for node_id, node in wf.items():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") == "CLIPTextEncode":
            inputs = node.get("inputs", {})
            if not positive_injected:
                inputs["text"] = positive
                positive_injected = True
            elif negative:
                inputs["text"] = negative

    return wf
