#!/usr/bin/env python3
"""Debug LLM entity extraction for eval ID 2"""

import sys, json, re, urllib.request
from pathlib import Path

USER_INTENT = "帮我生成一张海报，上面写着'秋日味道'，背景是秋天的树叶"

# Load config
ENGINE_DIR = Path(__file__).parent / "engine"
with open(ENGINE_DIR / "config.json", "r") as f:
    cfg = json.load(f)

vision_cfg = cfg.get("vision_model", {})
base_url = vision_cfg.get("base_url", "")
model = vision_cfg.get("model", "qwen3.6-plus")
api_key = vision_cfg.get("api_key_env", "")

# Build prompt
SYSTEM_PROMPT = """You extract image generation intent into structured tags.
Return a JSON array of entity tags matching these categories:
subject, style, mood, composition, lighting, background, color_palette, genre

Rules:
- Only return tags that exist in the catalog below, or construct new ones as category:value
- If the user's description matches a known entity, use that exact tag
- Return ONLY a JSON array, no explanation
- If no entities can be extracted, return an empty array

Known entities:
subject:cat, subject:person, subject:food, subject:landscape, subject:animal,
style:watercolor, style:photography, style:digital_art, style:illustration, style:oil_painting, style:sketch,
mood:warm, mood:peaceful, mood:energetic, mood:mysterious,
composition:close_up, composition:wide_shot, composition:centered,
lighting:natural, lighting:studio, lighting:golden_hour,
background:indoor, background:outdoor, background:abstract,
color_palette:warm, color_palette:cool, color_palette:pastel,
genre:poster, genre:infographic, genre:cover
"""

user_prompt = f"Extract seed entities from: {USER_INTENT}"
full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

# Build API URL
base = base_url.rstrip("/")
api_url = f"{base}/chat/completions"
print(f"API URL: {api_url}")
print(f"Model: {model}")
print(f"Prompt length: {len(full_prompt)}")
print(f"---")
print(f"Full prompt:\n{full_prompt}")
print(f"---")

payload = {
    "model": model,
    "messages": [
        {"role": "user", "content": full_prompt}
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

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        print(f"Status: {resp.status}")
        msg = body["choices"][0]["message"]
        text = msg.get("content") or msg.get("reasoning_content") or ""
        print(f"Raw response:\n{text}")

        # Parse
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            entities = json.loads(json_match.group())
            print(f"Parsed entities: {entities}")
        else:
            print("No JSON array found in response")
except Exception as e:
    print(f"ERROR: {e}")
