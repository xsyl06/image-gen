"""Intent Recognition — extract KG seed entities from natural language.

Uses the configured vision/chat model (OpenAI-compatible API) to parse
user intent into structured entity tags. Falls back to keyword matching
if the model is unreachable.
"""

import json
import os
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


def _build_catalog_preview():
    """Build catalog preview with Chinese names for LLM system prompt."""
    _load_catalog()
    items = []
    for tag in sorted(_ENTITY_CATALOG.keys()):
        info = _ENTITY_CATALOG[tag]
        name_zh = info.get("name_zh", "")
        if name_zh:
            items.append(f"{tag} ({name_zh})")
        else:
            items.append(tag)
    preview = ", ".join(items[:30])
    if len(_ENTITY_CATALOG) > 30:
        preview += f" ... ({len(_ENTITY_CATALOG)} total)"
    return preview


# ── LLM-based extraction ─────────────────────────────────

_SYSTEM_PROMPT = """你是一个图像生成意图识别专家。从用户描述中提取结构化标签。

可用类别: subject, style, mood, composition, lighting, background, color_palette, color, genre, technique, texture, theme

规则:
- 仔细分析用户描述中的每一个视觉元素，确保不遗漏
- 从下方实体目录中匹配已知实体 — 使用目录中显示的精确标签
- 如果用户描述中的实体不在目录中，使用上述类别构造标签，值用英文小写+下划线格式（如 subject:japanese_bento, style:korean_street_fashion）
- 必须提取所有可检测到的实体，包括：主体、风格、氛围、构图、光线、背景、色彩等
- 中文描述要逐句分析，识别所有名词和形容词对应的视觉元素
- 仅返回 JSON 数组，不要解释

已知实体 (格式: tag (中文名)):
{catalog}
"""

_USER_PROMPT_TEMPLATE = "从以下图像描述中提取所有视觉实体标签（支持中文和英文输入）:\n{intent}"


def _call_chat_api(message, cfg):
    """Call the configured chat/vision model (OpenAI-compatible API)."""
    # Config uses flat keys: vision_api_url, vision_model (string), vision_api_key
    base_url = cfg.get("vision_api_url", "")
    model = cfg.get("vision_model", "qwen3.6-plus")
    api_key = cfg.get("vision_api_key", "") or os.environ.get("VISION_API_KEY", "")

    if not base_url:
        raise ValueError("No chat API configured. Set vision_api_url in engine/config.json")

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
        "max_tokens": 512,
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

    # Build catalog preview with Chinese names for better entity matching
    catalog_preview = _build_catalog_preview()

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
    # ── English ──────────────────────────────────────────────
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
    # ── Chinese ──────────────────────────────────────────────
    "猫": "subject:cat",
    "小猫": "subject:cat",
    "人物": "subject:person",
    "人": "subject:person",
    "肖像": "subject:person",
    "美食": "subject:food",
    "食物": "subject:food",
    "风景": "subject:landscape",
    "动物": "subject:animal",
    "狗": "subject:animal",
    "鸟": "subject:animal",
    "水彩": "style:watercolor",
    "摄影": "style:photography",
    "照片": "style:photography",
    "数字艺术": "style:digital_art",
    "插画": "style:illustration",
    "油画": "style:oil_painting",
    "素描": "style:sketch",
    "温馨": "mood:warm",
    "温暖": "mood:warm",
    "宁静": "mood:peaceful",
    "平静": "mood:peaceful",
    "活力": "mood:energetic",
    "神秘": "mood:mysterious",
    "特写": "composition:close_up",
    "远景": "composition:wide_shot",
    "全景": "composition:wide_shot",
    "居中": "composition:centered",
    "居中构图": "composition:centered",
    "自然光": "lighting:natural",
    "阳光": "lighting:golden_hour",
    "黄金时刻": "lighting:golden_hour",
    "棚拍": "lighting:studio",
    "室内": "background:indoor",
    "室外": "background:outdoor",
    "户外": "background:outdoor",
    "抽象": "background:abstract",
    "暖色调": "color_palette:warm",
    "冷色调": "color_palette:cool",
    "粉彩": "color_palette:pastel",
    "海报": "genre:poster",
    "信息图": "genre:infographic",
    "封面": "genre:cover",
    "小丑": "subject:clown",
    "马戏团": "background:circus",
    "水下": "background:underwater",
    "电影感": "mood:ethereal",
    "空灵": "mood:ethereal",
    "明亮": "lighting:bright",
    "欢快": "mood:cheerful",
    # ── Food / 美食 ──────────────────────────────
    "甜品": "subject:dessert",
    "蛋糕": "subject:cake",
    "草莓": "subject:strawberry",
    "咖啡": "subject:coffee",
    "下午茶": "subject:afternoon_tea",
    "便当": "subject:bento",
    "寿司": "subject:sushi",
    "沙拉": "subject:salad",
    "水果": "subject:fruit",
    "美食摄影": "style:food_photography",
    "ins风": "style:instagram",
    # ── Fashion / 穿搭 ───────────────────────────
    "穿搭": "subject:fashion",
    "街拍": "style:street_photography",
    "韩系": "style:korean",
    "法式": "style:french",
    "连衣裙": "subject:dress",
    "西装": "subject:blazer",
    "时尚": "style:fashion",
    "博主": "style:influencer",
    # ── Travel / 旅行 ────────────────────────────
    "海岛": "subject:island",
    "度假": "theme:vacation",
    "沙滩": "background:beach",
    "日落": "lighting:sunset",
    "夕阳": "lighting:sunset",
    "古寺": "subject:temple",
    "红叶": "subject:autumn_leaves",
    "枫叶": "subject:maple_leaves",
    "鸟居": "subject:torii_gate",
    "石灯笼": "subject:stone_lantern",
    "秋日": "mood:autumn",
    "京都": "background:kyoto",
    # ── Home / 家居 ──────────────────────────────
    "卧室": "subject:bedroom",
    "北欧": "style:nordic",
    "书房": "subject:study_room",
    "书桌": "subject:desk",
    "台灯": "subject:desk_lamp",
    "绿植": "subject:plants",
    "居家": "style:homestyle",
    "简约": "style:minimalist",
    "简洁": "style:minimalist",
    "木质": "texture:wooden",
    "木地板": "background:wooden_floor",
    # ── Beauty / 美妆 ────────────────────────────
    "护肤品": "subject:skincare",
    "口红": "subject:lipstick",
    "美妆": "style:beauty",
    "精华液": "subject:serum",
    "面霜": "subject:cream",
    "面膜": "subject:face_mask",
    "玫瑰花瓣": "subject:rose_petals",
    "大理石": "background:marble",
    "试色": "style:swatch",
    # ── Lifestyle / 生活方式 ──────────────────────
    "拉花": "subject:latte_art",
    "咖啡师": "subject:barista",
    "手账": "subject:journal",
    "手帐": "subject:journal",
    "马克笔": "subject:markers",
    "胶带": "subject:washi_tape",
    "拍立得": "subject:polaroid",
    "治愈": "mood:healing",
    "治愈系": "mood:healing",
    "惬意": "mood:cozy",
    "舒适": "mood:cozy",
    # ── Illustration / 插画 ──────────────────────
    "水彩插画": "style:watercolor_illustration",
    "手绘": "style:hand_drawn",
    "宫崎骏": "style:miyazaki",
    "山坡": "background:hillside",
    "木屋": "subject:cabin",
    "风车": "subject:windmill",
    "野花": "subject:wildflowers",
    "樱花": "subject:cherry_blossom",
    "清新": "mood:fresh",
    # ── Lighting & Color ─────────────────────────
    "侧光": "lighting:side_light",
    "柔光": "lighting:soft_light",
    "暖光": "lighting:warm_light",
    "暖黄光": "lighting:warm_yellow",
    "逆光": "lighting:backlight",
    "暖粉": "color_palette:warm_pink",
    "粉彩": "color_palette:pastel",
    "碧蓝": "color:blue",
    "金色": "color:gold",
    # ── Composition ──────────────────────────────
    "俯拍": "composition:top_down",
    "平铺": "composition:flat_lay",
    "全身照": "composition:full_body",
    "竖版": "composition:portrait",
    "广角": "composition:wide_angle",
    "全景": "composition:panorama",
    "浅景深": "technique:shallow_dof",
    "虚化": "technique:bokeh",
    "微距": "composition:macro",
    # ── Other ────────────────────────────────────
    "精致": "mood:refined",
    "高端": "mood:premium",
    "杂志": "style:magazine",
    "纪实": "style:documentary",
    "人文": "style:humanistic",
    "慵懒": "mood:relaxed",
    "清新": "mood:fresh",
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
