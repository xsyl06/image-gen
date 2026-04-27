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
# Loaded from prompt_graph.json at init time. Used to ground
# extraction to known entities while still allowing unknowns.

_ENTITY_CATALOG = None
_CATEGORY_PREFIXES = None


def _load_catalog():
    global _ENTITY_CATALOG, _CATEGORY_PREFIXES
    if _ENTITY_CATALOG is not None:
        return
    from pathlib import Path
    graph_path = Path(__file__).parent / "kg" / "data" / "prompt_graph.json"
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
Available categories: subject, style, mood, composition, lighting, background, color_palette, color, genre, technique, texture, theme

Rules:
- Match known entities from the catalog below — use the EXACT tag shown
- If the user's entity is NOT in the catalog, construct a tag as category:value using the category from the list above
- Always return all detectable entities — never omit unknown ones
- Return ONLY a JSON array, no explanation

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
    If both return empty, extracts a subject keyword from user input.

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

    seeds = _keyword_fallback(user_intent)
    if not seeds:
        seeds = [_extract_subject_fallback(user_intent)]
    return seeds


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

    return unique


# ── Fallback extraction ───────────────────────────────────

# English stop words — only removed when input is primarily English
_EN_STOP_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "is", "it",
    "that", "with", "by", "from", "and", "or", "but", "not", "this",
    "some", "very", "so", "just", "like", "have", "has", "be", "my",
    "your", "his", "her", "its", "our", "their", "what", "which", "who",
    "would", "could", "should", "will", "shall", "may", "might",
    "i", "you", "he", "she", "we", "they", "me", "him", "them",
    "one", "make", "want", "need", "see", "look", "get", "give",
}

# Chinese measure words / function words to strip from the front
# These appear in patterns like "一只狐狸", "画一张城市"
_CN_PREFIXES = [
    "一只", "一幅", "一张", "一条", "一朵", "一头", "一匹", "一个", "一些",
    "只", "幅", "张", "条", "朵", "头", "匹", "个", "些",
    "这", "那", "此",
]

# Chinese particles to strip (NOT subject words like 人/猫/狗)
_CN_PARTICLES = ["的", "了", "着", "过", "呢", "啊", "吧", "嘛"]


def _extract_subject_fallback(user_intent):
    """Extract a subject keyword from user input when all else fails.

    Uses language-aware extraction: English words are split on spaces after
    stop word removal, while Chinese text strips measure words and particles
    to reveal the core subject noun.
    """
    text = user_intent.strip()
    if not text:
        return "subject:unknown"

    # Detect if input is primarily Chinese
    has_cjk = any('一' <= c <= '鿿' for c in text)

    if has_cjk:
        return _extract_chinese_subject(text)
    else:
        return _extract_english_subject(text.lower())


def _extract_chinese_subject(text):
    """Extract subject from Chinese text by stripping measure words and particles."""
    # Strip leading measure words: "一只狐狸" → "狐狸"
    for prefix in _CN_PREFIXES:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break

    # Strip trailing particles: "狐狸啊" → "狐狸"
    for particle in _CN_PARTICLES:
        if text.endswith(particle):
            text = text[:-len(particle)]
            break

    # Remove "的" from middle: "银色的猫" → "银色猫"
    text = text.replace("的", "")

    # Remove common verb prefixes that aren't the subject
    for verb in ["画", "生成", "创建", "做", "画一个", "画一张"]:
        if text.startswith(verb):
            text = text[len(verb):]
            break

    text = text.strip()
    if text:
        return f"subject:{text}"
    return f"subject:{text.strip()}"


def _extract_english_subject(text):
    """Extract subject from English text by removing stop words."""
    # Remove multi-word stop phrases first
    for sw in ["in the", "on the", "at the"]:
        text = text.replace(sw, " ")

    # Remove single-word stop words
    words = text.split()
    filtered = [w for w in words if w not in _EN_STOP_WORDS]

    if filtered:
        return f"subject:{' '.join(filtered)}"
    # Absolute last resort
    return f"subject:{text.strip()}"
