"""Intent Recognition — extract KG seed entities from natural language.

Uses the configured vision/chat model (OpenAI-compatible API) to parse
user intent into structured entity tags. Falls back to keyword matching
if the model is unreachable.
"""

import json
import re
import urllib.error
import urllib.request

# ── Entity catalog ────────────────────────────────────────
# Loaded from prompt-graph.json at init time. Used to ground
# extraction to known entities while still allowing unknowns.

_ENTITY_CATALOG = None
_CATEGORY_PREFIXES = None


def _load_catalog():
    global _ENTITY_CATALOG, _CATEGORY_PREFIXES
    if _ENTITY_CATALOG is not None:
        return
    from pathlib import Path
    graph_path = Path(__file__).parent / "kg" / "data" / "prompt-graph.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _ENTITY_CATALOG = data.get("entities", {})
    _CATEGORY_PREFIXES = {}
    for tag in _ENTITY_CATALOG:
        if ":" in tag:
            cat = tag.split(":")[0]
            _CATEGORY_PREFIXES.setdefault(cat, []).append(tag)


# ── LLM-based extraction ─────────────────────────────────

_SYSTEM_PROMPT = """You extract image generation intent into structured tags.
Return a JSON array of entity tags matching these categories:
subject, style, mood, composition, lighting, background, color_palette, genre

Rules:
- Only return tags that exist in the catalog below, or construct new ones as category:value
- If the user's description matches a known entity, use that exact tag
- Return ONLY a JSON array, no explanation
- If no entities can be extracted, return an empty array

Known entities:
{catalog}
"""

_USER_PROMPT_TEMPLATE = "Extract seed entities from: {intent}"


def _call_chat_api(message, cfg):
    """Call the configured chat/vision model (OpenAI-compatible API)."""
    vision_cfg = cfg.get("vision_model", {})
    base_url = vision_cfg.get("base_url", "")
    model = vision_cfg.get("model", "qwen3.6-plus")
    api_key = vision_cfg.get("api_key_env", "")

    if not base_url:
        raise ValueError("No chat API configured. Set vision_model.base_url in engine/config.json")

    # Strip /v1 suffix if present, then add /chat/completions
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        api_url = f"{base}/chat/completions"
    else:
        api_url = f"{base}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": message}
        ],
        "max_tokens": 256,
        "temperature": 0.1,
    }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    msg = body["choices"][0]["message"]
    text = msg.get("content") or msg.get("reasoning_content") or ""
    text = re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE).strip()
    return text


def extract_seed_entities_llm(user_intent, cfg):
    """Extract seed entities using LLM.

    Falls back to keyword-based extraction if the API call fails.

    Args:
        user_intent: Natural language description
        cfg: Config dict with vision_model settings

    Returns:
        List of entity tag strings, e.g. ["subject:cat", "style:watercolor"]
    """
    _load_catalog()

    # Build catalog preview for the prompt
    catalog_preview = ", ".join(sorted(_ENTITY_CATALOG.keys())[:30])
    if len(_ENTITY_CATALOG) > 30:
        catalog_preview += f" ... ({len(_ENTITY_CATALOG)} total)"

    system_prompt = _SYSTEM_PROMPT.format(catalog=catalog_preview)
    user_prompt = _USER_PROMPT_TEMPLATE.format(intent=user_intent)
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    try:
        response = _call_chat_api(full_prompt, cfg)
        # Parse JSON array from response
        json_match = re.search(r'\[[\s\S]*\]', response)
        if json_match:
            entities = json.loads(json_match.group())
            if isinstance(entities, list):
                # Validate format: each should be "category:value"
                valid = [e for e in entities if isinstance(e, str) and ":" in e]
                if valid:
                    return valid
    except Exception:
        pass  # Fall through to keyword fallback

    return _keyword_fallback(user_intent)


# ── Keyword fallback ──────────────────────────────────────

_KEYWORD_MAP = {
    "cat": "subject:cat",
    "cats": "subject:cat",
    "kitten": "subject:cat",
    "person": "subject:person",
    "people": "subject:person",
    "portrait": "subject:person",
    "food": "subject:food",
    "meal": "subject:food",
    "landscape": "subject:landscape",
    "scenery": "subject:landscape",
    "animal": "subject:animal",
    "dog": "subject:animal",
    "bird": "subject:animal",
    "watercolor": "style:watercolor",
    "photography": "style:photography",
    "photo": "style:photography",
    "digital art": "style:digital_art",
    "digital": "style:digital_art",
    "illustration": "style:illustration",
    "oil painting": "style:oil_painting",
    "sketch": "style:sketch",
    "warm": "mood:warm",
    "cozy": "mood:warm",
    "peaceful": "mood:peaceful",
    "calm": "mood:peaceful",
    "energetic": "mood:energetic",
    "dynamic": "mood:energetic",
    "mysterious": "mood:mysterious",
    "close-up": "composition:close_up",
    "close up": "composition:close_up",
    "wide shot": "composition:wide_shot",
    "centered": "composition:centered",
    "natural light": "lighting:natural",
    "sunlight": "lighting:golden_hour",
    "golden hour": "lighting:golden_hour",
    "studio": "lighting:studio",
    "indoor": "background:indoor",
    "outdoor": "background:outdoor",
    "abstract": "background:abstract",
    "warm tones": "color_palette:warm",
    "cool tones": "color_palette:cool",
    "pastel": "color_palette:pastel",
    "poster": "genre:poster",
    "infographic": "genre:infographic",
    "cover": "genre:cover",
}


def _keyword_fallback(user_intent):
    """Keyword-based entity extraction (fallback)."""
    seeds = []
    intent_lower = user_intent.lower()

    # Sort by length descending to match longer phrases first
    for keyword in sorted(_KEYWORD_MAP.keys(), key=len, reverse=True):
        if keyword in intent_lower:
            seeds.append(_KEYWORD_MAP[keyword])

    # Remove duplicates (longer match wins due to sort order)
    seen = set()
    unique = []
    for s in seeds:
        if s not in seen:
            seen.add(s)
            unique.append(s)

    return unique if unique else ["subject:cat"]
