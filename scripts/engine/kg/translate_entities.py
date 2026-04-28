#!/usr/bin/env python3
"""Translate entity names in prompt_graph.json to Chinese using LLM.

Usage:
    python scripts/engine/kg/translate_entities.py
"""

import json
import re
import urllib.request
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "data" / "prompt_graph.json"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"

BATCH_SIZE = 30  # entities per API call


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_vision_config():
    """Read vision model config from engine/config.json."""
    cfg = load_config()
    model = cfg.get("vision_model", "qwen3.6-plus")
    if isinstance(model, dict):
        base_url = model.get("base_url", "")
        model_name = model.get("model", "qwen3.6-plus")
        api_key = model.get("api_key_env", "")
    else:
        base_url = cfg.get("vision_api_url", "")
        model_name = model
        api_key = cfg.get("vision_api_key", "")

    if not base_url or not api_key:
        raise ValueError("Vision API not configured. Check engine/config.json")

    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        api_url = base
    else:
        api_url = f"{base}/chat/completions"

    return api_url, model_name, api_key


def load_entities():
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["entities"]


def translate_batch(entities_dict, batch_keys, api_url, model, api_key):
    """Translate a batch of entity names to Chinese."""
    lines = []
    for tag in batch_keys:
        info = entities_dict[tag]
        cat = info["category"]
        name = info["name"]
        lines.append(f"- [{cat}] {tag} -> \"{name}\"")

    prompt = (
        "以下是图像生成知识图谱中的实体名称。请将每个实体的 name 字段翻译"
        "成简洁准确的中文。翻译要求：\n"
        "1. 颜色类保持英文原名（red→red, blue→blue）\n"
        "2. 专业术语保留英文原名并在括号中附中文说明（如 dolly zoom→dolly zoom（滑动变焦））\n"
        "3. 其他实体直接给出地道中文翻译，不需要括号附英文\n"
        "4. 返回严格的 JSON 对象，key 是原始 tag，value 是中文翻译\n"
        "5. 不要返回任何额外文字或解释\n"
        "实体列表：\n" + "\n".join(lines)
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "你是一个专业的翻译助手，只返回 JSON 格式的结果。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.1,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

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

    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json.loads(json_match.group())
    return {}


def main():
    entities = load_entities()
    print(f"Loaded {len(entities)} entities")

    # Skip already translated
    already = [tag for tag, info in entities.items() if info.get("name_zh")]
    print(f"Already translated: {len(already)}")

    remaining = [tag for tag, info in entities.items() if not info.get("name_zh")]
    print(f"Remaining to translate: {len(remaining)}")

    if not remaining:
        print("All entities already have Chinese names.")
        return

    # Read vision model config
    api_url, model, api_key = get_vision_config()
    print(f"Using model: {model}")

    # Process in batches
    results = {}
    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i:i+BATCH_SIZE]
        print(f"\nBatch {i//BATCH_SIZE + 1}/{(len(remaining)+BATCH_SIZE-1)//BATCH_SIZE} "
              f"({len(batch)} entities)...")
        try:
            batch_result = translate_batch(entities, batch, api_url, model, api_key)
            results.update(batch_result)
            print(f"  Got {len(batch_result)} translations")
        except Exception as e:
            print(f"  ERROR: {e}")

    # Merge back
    print(f"\nMerging {len(results)} translations into prompt_graph.json...")
    for tag, name_zh in results.items():
        if tag in entities:
            entities[tag]["name_zh"] = name_zh

    # Save
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    raw["entities"] = entities

    with open(GRAPH_PATH, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"Done! Updated {len(results)} entities with Chinese names.")


if __name__ == "__main__":
    main()
