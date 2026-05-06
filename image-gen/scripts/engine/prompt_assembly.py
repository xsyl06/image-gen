"""Prompt Assembly — build structured JSON prompts from KG skeleton + user intent.

Combines KG recommendations with raw LLM-extracted seeds, detects
confrontation/comparison intent, and assembles a complete JSON prompt.
"""


def _detect_confrontation(json_prompt, user_intent):
    """Detect left-vs-right or top-vs-bottom comparison intent from user description."""
    lower = user_intent.lower()

    is_comparison = any(kw in lower for kw in [
        "left vs right", "left_vs_right", "对比", "对比图",
        "comparison image", "compare", " versus ", "对照",
    ])

    if not is_comparison:
        return

    layout = "left_vs_right"
    if any(kw in lower for kw in ["top vs", "top_vs", "above vs", "上下", "上下对比"]):
        layout = "top_vs_bottom"

    import re
    if layout == "left_vs_right":
        lr_pattern = r'([^,]+?)\s+on\s+the\s+left[^,]*,\s*([^,]+?)\s+on\s+the\s+right'
        lr_match = re.search(lr_pattern, lower)

        if lr_match:
            left_desc = lr_match.group(1).strip()
            right_desc = lr_match.group(2).strip()
        else:
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
       use the LLM-extracted value directly
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

    filled_cats = set()

    # 1. Fill from KG skeleton.filled (known entities)
    for category, entity_info in skeleton.get("filled", {}).items():
        entity_tag = entity_info.get("entity", "")
        value = entity_tag.split(":")[-1] if ":" in entity_tag else entity_tag
        field = field_map.get(category, category)
        json_prompt[field] = value
        filled_cats.add(category)

    # 2. Fill from raw LLM seeds for categories KG didn't recognize
    if seeds:
        for seed in seeds:
            if ":" in seed:
                cat, value = seed.split(":", 1)
                field = field_map.get(cat, cat)
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

    # Detect confrontation/comparison intent
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
