#!/usr/bin/env python3
"""Translate new entity names to Chinese (background process).

Called by kg_update.py via subprocess.Popen.
Args: tag1=name1 tag2=name2 ...
"""
import json
import re
import sys
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "data" / "prompt_graph.json"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def call_llm(prompt_text):
    cfg_path = CONFIG_PATH
    if not cfg_path.exists():
        return None
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    # config.json has vision_model as string + top-level api fields
    model = cfg.get("vision_model", "qwen3.6-plus")
    if isinstance(model, dict):
        base_url = model.get("base_url", "")
        api_key = model.get("api_key_env", "")
        model_name = model.get("model", "qwen3.6-plus")
    else:
        base_url = cfg.get("vision_api_url", "")
        api_key = cfg.get("vision_api_key", "")
        model_name = model
    if not base_url or not api_key:
        return None

    base = base_url.rstrip("/")
    # URL may already include /chat/completions
    if not base.endswith("/chat/completions"):
        api_url = f"{base}/chat/completions"
    else:
        api_url = base

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "只返回JSON，不要任何解释。"},
            {"role": "user", "content": prompt_text}
        ],
        "max_tokens": 512,
        "temperature": 0.1,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    import urllib.request
    req = urllib.request.Request(
        api_url, data=json.dumps(payload).encode("utf-8"),
        headers=headers, method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    text = body["choices"][0]["message"]["content"]
    text = re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE).strip()
    return text


def main():
    if len(sys.argv) < 2:
        return

    pairs = []
    for arg in sys.argv[1:]:
        if "=" in arg:
            tag, name = arg.split("=", 1)
            pairs.append((tag, name))

    if not pairs:
        return

    # Batch translate all entities
    names_str = ", ".join(f'"{name}"' for _, name in pairs)
    result = call_llm(f"翻译以下{len(pairs)}个图像生成术语为中文，返回JSON对象，key是原英文，value是中文翻译：{names_str}")
    if not result:
        return

    json_match = re.search(r'\{[\s\S]*\}', result)
    if not json_match:
        return

    try:
        translations = json.loads(json_match.group())
    except json.JSONDecodeError:
        return

    # Update graph
    with open(GRAPH_PATH, "r", encoding="utf-8") as f:
        graph = json.load(f)

    updated = False
    for tag, name in pairs:
        if tag in graph.get("entities", {}):
            zh = translations.get(name, name)
            graph["entities"][tag]["name_zh"] = zh
            updated = True

    if updated:
        with open(GRAPH_PATH, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
