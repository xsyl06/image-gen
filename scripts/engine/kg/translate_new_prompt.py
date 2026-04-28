#!/usr/bin/env python3
"""Translate a new prompt_index entry to Chinese (background process).

Called by kg_update.py via subprocess.Popen.
Arg: JSON payload string
"""
import json
import re
import sys
from pathlib import Path

GRAPH_PATH = Path(__file__).parent / "data" / "prompt_graph.json"
CONFIG_PATH = Path(__file__).parent.parent / "config.json"


def call_llm(prompt_text):
    if not CONFIG_PATH.exists():
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
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
            {"role": "system", "content": "返回JSON格式：{\"title_zh\": \"中文标题\", \"prompt_zh\": \"中文描述\"}，不要任何解释。"},
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

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        return

    title = payload.get("title", "")
    prompt = payload.get("prompt", "")
    graph_path = Path(payload.get("graph_path", str(GRAPH_PATH)))
    index = payload.get("index", -1)

    if index < 0:
        return

    result = call_llm(f"title: {title}\nprompt: {prompt}")
    if not result:
        return

    json_match = re.search(r'\{[\s\S]*\}', result)
    if not json_match:
        return

    try:
        translations = json.loads(json_match.group())
    except json.JSONDecodeError:
        return

    title_zh = translations.get("title_zh", title)
    prompt_zh = translations.get("prompt_zh", prompt[:150])

    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    prompt_index = graph.get("prompt_index", [])
    if index < len(prompt_index):
        prompt_index[index]["title_zh"] = title_zh
        prompt_index[index]["prompt_short_zh"] = prompt_zh

        with open(graph_path, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
