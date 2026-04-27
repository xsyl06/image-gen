#!/usr/bin/env python3
"""Debug vision API call"""

import sys, json
from pathlib import Path

ENGINE_DIR = Path(__file__).parent / "engine"
print(str(ENGINE_DIR))
sys.path.insert(0, str(ENGINE_DIR))

from comfyui import describe_image

# Use the first generated image
image_path = r"C:\Users\ww\image-gen-output\cli-run-001_20260425_225142_0.png"

# Load config
with open(ENGINE_DIR / "config.json", "r") as f:
    cfg = json.load(f)

# Print config keys for debugging
print("Config keys:", list(cfg.keys()))
print("vision_api_url:", cfg.get("vision_api_url"))
print("vision_api_key:", cfg.get("vision_api_key", "")[:10] + "...")
print("vision_model:", cfg.get("vision_model"))

prompt = """Evaluate this generated image. Score each dimension 1-10:
1. Subject Accuracy
2. Style Fidelity
3. Mood/Atmosphere
4. Composition Quality
5. Technical Quality
6. Overall Satisfaction

Return as JSON with keys: subject_accuracy, style_fidelity, mood_atmosphere, composition_quality, technical_quality, overall_satisfaction, weighted_score, strengths, weaknesses, improved_prompt"""

print("\nCalling vision API...")
try:
    result = describe_image(image_path, prompt, cfg)
    print("Result type:", type(result))
    print("Result keys:", result.keys() if isinstance(result, dict) else "N/A")
    print("Result:", json.dumps(result, indent=2, ensure_ascii=False, default=str)[:2000])
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
