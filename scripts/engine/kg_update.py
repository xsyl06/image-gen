"""KG Update — accumulate experience from successful generations.

After a generation passes the quality threshold, record the prompt
combination in the Knowledge Graph so future skeleton queries benefit
from the learned entity co-occurrences.
"""

import json
import sys
from itertools import combinations
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "kg" / "data" / "prompt_graph.json"


def update_kg(used_entities, positive_prompt, score, threshold=8):
    """Record a successful generation in the KG.

    Args:
        used_entities: List of entity tags used (e.g. ["subject:cat", "style:watercolor"])
        positive_prompt: The positive prompt text (for prompt_index)
        score: Final evaluation weighted_score
        threshold: Minimum score to record (default 8)

    Returns:
        True if KG was updated, False otherwise
    """
    if score < threshold:
        return False

    if not GRAPH_PATH.exists():
        print(f"Warning: KG file not found at {GRAPH_PATH}", file=sys.stderr)
        return False

    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    updated = False

    # 1. Increment co-occurrence counts for each entity pair
    for e1, e2 in combinations(used_entities, 2):
        if e1 not in graph["co_occurrence"]:
            graph["co_occurrence"][e1] = {}
        if e2 not in graph["co_occurrence"][e1]:
            graph["co_occurrence"][e1][e2] = 0
        graph["co_occurrence"][e1][e2] += 1
        updated = True

    # 2. Add to prompt_index if novel combination
    existing_tag_sets = {
        frozenset(p["tags"]) for p in graph.get("prompt_index", [])
    }
    if frozenset(used_entities) not in existing_tag_sets:
        title = _generate_title(used_entities)
        # Fallback to English; translated asynchronously
        title_zh = ""
        prompt_short_zh = ""
        entry = {
            "id": f"p-{len(graph.get('prompt_index', [])) + 1:03d}",
            "title": title,
            "title_zh": title_zh,
            "tags": list(used_entities),
            "prompt_short": positive_prompt[:150] if positive_prompt else "",
            "prompt_short_zh": prompt_short_zh,
        }
        graph.setdefault("prompt_index", []).append(entry)
        updated = True

        # Asynchronously translate (non-blocking)
        new_idx = len(graph["prompt_index"]) - 1
        _translate_prompt_async(entry, GRAPH_PATH, new_idx)

    # 3. Ensure new entities exist in entities dict
    new_entities = []
    for tag in used_entities:
        if tag not in graph.get("entities", {}):
            if ":" in tag:
                cat, name = tag.split(":", 1)
            else:
                cat, name = "unknown", tag
            graph.setdefault("entities", {})[tag] = {
                "category": cat,
                "name": name,
                "name_zh": name,  # Fallback to English; translated asynchronously below
                "count": 1,
            }
            new_entities.append((tag, name))
        else:
            graph["entities"][tag]["count"] += 1

    # 3b. Asynchronously translate new entity names (non-blocking)
    if new_entities:
        _translate_entities_async(new_entities, GRAPH_PATH)

    # Save if anything changed
    if updated:
        with open(GRAPH_PATH, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)

    return updated


def _generate_title(entities):
    """Generate a short title from entity tags."""
    parts = []
    for tag in entities[:3]:  # Use first 3 entities max
        if ":" in tag:
            parts.append(tag.split(":", 1)[1])
        else:
            parts.append(tag)
    return " ".join(parts) if parts else "Untitled"


# ── LLM translation helpers ──────────────────────────────

def _translate_entities_async(new_entities, graph_path):
    """Launch background process to translate entity names to Chinese."""
    import subprocess
    script = Path(__file__).parent / "kg" / "translate_new_entities.py"
    if script.exists():
        args = [str(script)] + [f"{tag}={name}" for tag, name in new_entities]
        subprocess.Popen(
            [sys.executable] + args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _translate_prompt_async(entry, graph_path, index):
    """Launch background process to translate a prompt_index entry."""
    import subprocess
    script = Path(__file__).parent / "kg" / "translate_new_prompt.py"
    if script.exists():
        payload = json.dumps({
            "title": entry["title"],
            "prompt": entry["prompt_short"],
            "graph_path": str(graph_path),
            "index": index,
        })
        subprocess.Popen(
            [sys.executable, str(script), payload],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
