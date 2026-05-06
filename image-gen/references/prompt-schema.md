# JSON Prompt Schema (13 Dimensions)

## Overview

The image-gen skill uses a structured JSON prompt format with 13 dimensions for better generation quality compared to plain text. Each dimension aligns with KG entity categories and can be automatically assembled from skeleton output.

**Key advantages:**
- Better control over generation parameters
- Automatic conversion to model-friendly natural language
- Alignment with KG recommendations
- Support for Chinese text rendering DSL

---

## Field Overview

All fields are optional. Use string for simple values, object for fine-grained control.

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `subject` | string/object | Main subject content | Recommended |
| `style` | string/object | Artistic style | Recommended |
| `mood` | string/object | Emotional atmosphere | Recommended |
| `composition` | object | Composition method | Optional |
| `lighting` | object | Lighting setup | Optional |
| `background` | object | Background environment | Optional |
| `color_palette` | object | Color scheme | Optional |
| `text_content` | object | Text in image | Optional (for text images) |
| `typography_layout` | object | Chinese typography DSL | Optional (advanced) |
| `confrontation` | object | Contrast composition | Optional (advanced) |
| `technical_specs` | object | Quality/rendering params | Optional |
| `layout` | string/object | Text layout | Recommended (for text images) |
| `negative_constraints` | list | Exclusion items | Recommended |

---

## 1. subject — Main Subject

### Type: `string` or `object`

### Purpose
Describe the main subject of the image.

### Simple Usage (String)
```json
{
  "subject": "a cat sitting on a windowsill"
}
```

### Object Usage (Fine-grained)
```json
{
  "subject": {
    "main": "a young woman reading a book",
    "details": "sitting cross-legged, glasses, focused expression",
    "position": "center of frame",
    "action": "reading intently",
    "accessories": ["glasses", "book", "coffee cup"]
  }
}
```

### KG Entity Mapping
- `subject:cat` → "a cat"
- `subject:person` → "a person"
- `subject:food` → "food photography"
- `subject:landscape` → "landscape scene"

---

## 2. style — Artistic Style

### Type: `string` or `object`

### Purpose
Define the artistic style and medium.

### Simple Usage
```json
{
  "style": "watercolor painting"
}
```

### Object Usage
```json
{
  "style": {
    "medium": "digital illustration",
    "techniques": ["watercolor wash", "ink outlines"],
    "references": "Studio Ghibli background art",
    "quality": "high detail, soft edges"
  }
}
```

### KG Entity Mapping
- `style:watercolor` → {"medium": "watercolor painting"}
- `style:photography` → {"medium": "photography", "quality": "high resolution"}
- `style:digital_art` → {"medium": "digital art"}
- `style:illustration` → {"medium": "illustration"}
- `style:oil_painting` → {"medium": "oil painting"}
- `style:sketch` → {"medium": "pencil sketch"}

---

## 3. mood — Emotional Atmosphere

### Type: `string` or `object`

### Purpose
Set the emotional tone and atmosphere.

### Simple Usage
```json
{
  "mood": "peaceful and serene"
}
```

### Object Usage
```json
{
  "mood": {
    "primary": "warm",
    "secondary": ["peaceful", "nostalgic"],
    "intensity": "moderate",
    "atmosphere": "cozy afternoon feeling"
  }
}
```

### KG Entity Mapping
- `mood:warm` → "warm atmosphere"
- `mood:peaceful` → "peaceful, serene"
- `mood:energetic` → "energetic, dynamic"
- `mood:mysterious` → "mysterious, intriguing"

---

## 4. composition — Composition Method

### Type: `object`

### Purpose
Define framing, angle, and visual layout.

### Example
```json
{
  "composition": {
    "framing": "medium shot",
    "angle": "slightly low angle",
    "focus": "the woman and her book",
    "depth": "layered composition",
    "rule": "rule of thirds",
    "orientation": "horizontal"
  }
}
```

### KG Entity Mapping
- `composition:close_up` → {"framing": "close-up shot"}
- `composition:wide_shot` → {"framing": "wide shot"}
- `composition:centered` → {"rule": "centered composition"}

---

## 5. lighting — Lighting Setup

### Type: `object`

### Purpose
Define light source, direction, and quality.

### Example
```json
{
  "lighting": {
    "type": "natural window light",
    "direction": "side lighting",
    "quality": "soft diffused",
    "color_temperature": "warm afternoon",
    "intensity": "moderate",
    "shadows": "soft shadows"
  }
}
```

### Simple Usage
```json
{
  "lighting": {"type": "natural", "quality": "soft"}
}
```

### KG Entity Mapping
- `lighting:natural` → {"type": "natural light"}
- `lighting:studio` → {"type": "studio lighting"}
- `lighting:golden_hour` → {"type": "golden hour", "color_temperature": "warm"}

---

## 6. background — Background Environment

### Type: `object`

### Purpose
Describe the setting and background details.

### Example
```json
{
  "background": {
    "setting": "indoor cozy room",
    "details": "bookshelves, plants, warm wooden furniture",
    "depth": "layered with bokeh",
    "color": "warm beige tones",
    "blur": "slight bokeh effect"
  }
}
```

### KG Entity Mapping
- `background:indoor` → {"setting": "indoor"}
- `background:outdoor` → {"setting": "outdoor"}
- `background:abstract` → {"setting": "abstract background"}

---

## 7. color_palette — Color Scheme

### Type: `object`

### Purpose
Define dominant colors and color mood.

### Example
```json
{
  "color_palette": {
    "dominant": ["warm beige", "soft amber"],
    "accent": ["sage green"],
    "mood": "warm and serene",
    "saturation": "moderate",
    "contrast": "low contrast"
  }
}
```

### Simple Usage
```json
{
  "color_palette": {"mood": "warm pastel"}
}
```

### KG Entity Mapping
- `color_palette:warm` → {"mood": "warm tones"}
- `color_palette:cool` → {"mood": "cool tones"}
- `color_palette:pastel` → {"mood": "pastel colors"}

---

## 8. text_content — Text in Image

### Type: `object`

### Purpose
Specify text that must appear in the image.

### Example
```json
{
  "text_content": {
    "visible_text": ["咖啡时光", "Café Dreams"],
    "typography": "handwritten style, chalkboard text",
    "language": "Chinese and English",
    "position": "top banner area",
    "style": "clear and readable"
  }
}
```

### Field Details
- `visible_text`: List of text strings to render
- `typography`: Font style description
- `language`: Language(s) of the text
- `position`: Approximate location
- `style`: Rendering quality requirements

**Important:** When using `text_content`, always include `layout` field.

---

## 9. typography_layout — Chinese Typography DSL

### Type: `object`

### Purpose
Advanced Chinese text layout control with position, color, gradient, and decoration support.

### Example
```json
{
  "typography_layout": {
    "style": "手写体，清晰可读",
    "lines": [
      {
        "position": "top",
        "segments": [
          {"text": "秋日味道", "color": "深棕", "style": "大号标题"}
        ]
      },
      {
        "position": "bottom_center",
        "segments": [
          {"text": "温暖每一刻", "color": {"from": "橘红", "to": "金黄", "direction": "从左到右"}}
        ],
        "emphasis": "带光晕效果"
      }
    ],
    "decorations": ["星星点缀", "落叶飘散"]
  }
}
```

### Position Values
`top`, `second`, `third`, `middle`, `center`, `bottom`, `bottom_center`, `bottom_left`, `bottom_right`, `top_left`, `top_right`, `left`, `right`

### Color Gradient
```json
{
  "color": {
    "from": "橘红",
    "to": "金黄",
    "direction": "从左到右"
  }
}
```

### Decoration Examples
- "星星点缀"
- "落叶飘散"
- "光晕效果"
- "边框装饰"

---

## 10. confrontation — Contrast Composition

### Type: `object`

### Purpose
Left/right or top/bottom comparison scenes.

### Example
```json
{
  "confrontation": {
    "layout": "left_vs_right",
    "left": {
      "name": "健康饮食",
      "color": "绿色",
      "feel": "清新活力",
      "details": "蔬菜水果，营养均衡"
    },
    "right": {
      "name": "垃圾食品",
      "color": "红色",
      "feel": "油腻沉重",
      "details": "油炸食品，不健康"
    }
  }
}
```

### Layout Values
- `left_vs_right`: Horizontal split
- `top_vs_bottom`: Vertical split

---

## 11. layout — Text Layout (Recommended)

### Type: `string` or `object`

### Purpose
Describe text element layout. **Required when `text_content` or `typography_layout` exists.**

### Simple String Usage
```json
{
  "layout": "顶部大标题'破茧成蝶'，底部五个阶段从左到右排列：卵→幼虫→蛹→成虫→飞翔"
}
```

### Structured Object Usage
```json
{
  "layout": {
    "elements": [
      {"role": "title", "text": "云梦泽", "position": "top-center"},
      {"role": "subtitle", "text": "古代大泽", "position": "below title"},
      {"role": "label", "text": "湖北江汉平原", "position": "left sidebar"}
    ],
    "typography": {
      "font_style": "serif",
      "color": "dark brown",
      "alignment": "center"
    },
    "connectors": ["ornate borders between sections"]
  }
}
```

### Design Principles
1. List each text element with exact content and position
2. Separate "what text" from "how to layout"
3. Use literal text values (model must copy exactly)
4. Specify precise positions (top-center, left sidebar, bottom banner)
5. Declare global typography rules centrally (font, color, alignment)

---

## 12. technical_specs — Quality/Rendering Parameters

### Type: `object`

### Purpose
Technical quality and rendering specifications.

### Example
```json
{
  "technical_specs": {
    "quality": "high quality, detailed",
    "resolution_hint": "1024x1024",
    "sharpness": "sharp details",
    "rendering": "professional photography",
    "noise": "low noise",
    "clarity": "crisp and clear"
  }
}
```

### Common Fields
- `quality`: General quality description
- `resolution_hint`: Target resolution guidance
- `sharpness`: Detail level
- `rendering`: Rendering style
- `noise`: Noise level control

---

## 13. negative_constraints — Exclusion Items

### Type: `list`

### Purpose
Define what to avoid in generation.

### Example
```json
{
  "negative_constraints": [
    "blurry",
    "distorted",
    "ugly",
    "deformed",
    "watermark",
    "低质量",
    "变形",
    "文字模糊",
    "错别字"
  ]
}
```

### Recommended Items
- `blurry`: Avoid blurry images
- `distorted`: Avoid distortion
- `watermark`: No watermarks
- `低质量`: Low quality (Chinese)
- `变形`: Deformation (Chinese)
- `文字模糊`: Blurred text (Chinese)

---

## Complete Example

### Full JSON Prompt
```json
{
  "subject": {
    "main": "a cat reading a book",
    "details": "on windowsill, focused expression",
    "position": "center of frame"
  },
  "style": {
    "medium": "watercolor painting",
    "techniques": ["soft wash", "ink outlines"],
    "quality": "high detail"
  },
  "mood": {
    "primary": "warm",
    "secondary": ["peaceful", "cozy"],
    "atmosphere": "afternoon sunlight feeling"
  },
  "composition": {
    "framing": "medium shot",
    "angle": "slightly low angle",
    "focus": "the cat and book"
  },
  "lighting": {
    "type": "natural window light",
    "direction": "side",
    "quality": "soft diffused",
    "color_temperature": "warm afternoon"
  },
  "background": {
    "setting": "indoor room",
    "details": "curtains, plants, warm furniture",
    "depth": "layered with soft bokeh"
  },
  "color_palette": {
    "dominant": ["warm beige", "soft amber"],
    "accent": ["sage green"],
    "mood": "warm pastel"
  },
  "technical_specs": {
    "quality": "high quality, detailed",
    "sharpness": "soft edges",
    "rendering": "watercolor style"
  },
  "negative_constraints": [
    "blurry",
    "distorted",
    "ugly",
    "watermark"
  ]
}
```

---

## Conversion to Text Prompt

The JSON prompt is automatically converted to model-friendly natural language by `json_prompt.py`:

```python
from json_prompt import json_prompt_to_text

result = json_prompt_to_text(json_prompt)
print(result["positive"])
# Output: "a cat reading a book on windowsill, focused expression, center of frame,
#          watercolor painting, soft wash, ink outlines, high detail, warm, peaceful, cozy,
#          afternoon sunlight feeling, medium shot, slightly low angle, natural window light..."

print(result["negative"])
# Output: "blurry, distorted, ugly, watermark"
```

---

## KG Skeleton → JSON Prompt Workflow

Typical workflow from KG skeleton output to JSON prompt:

1. **Get skeleton recommendations:**
```bash
kg.skeleton(["subject:cat", "style:watercolor"])
```

2. **Skeleton output:**
```json
{
  "filled": {
    "subject": {"entity": "subject:cat"},
    "style": {"entity": "style:watercolor"}
  },
  "recommendations": {
    "mood": [{"entity": "mood:warm", ...}],
    "lighting": [{"entity": "lighting:natural", ...}],
    "color_palette": [{"entity": "color_palette:pastel", ...}]
  }
}
```

3. **Assemble JSON prompt:**
```json
{
  "subject": "a cat",
  "style": {"medium": "watercolor"},
  "mood": "warm",
  "lighting": {"type": "natural"},
  "color_palette": {"mood": "pastel"}
}
```

---

## Validation

Use `validate_json_prompt()` to check prompt structure:

```python
from json_prompt import validate_json_prompt

issues = validate_json_prompt(json_prompt)
print(issues)
# Output: [] (empty if valid)
```

### Common Validation Warnings
- Missing `layout` when `text_content` exists
- Missing `negative_constraints`
- Very long `subject` description
- Incompatible `style` + `subject` combination

---

## Best Practices

1. **Start with KG skeleton:** Use skeleton recommendations for consistent style combinations
2. **Include negative_constraints:** Always specify what to avoid
3. **Use layout for text images:** Required when rendering Chinese text
4. **Keep subject concise:** Avoid overly long descriptions
5. **Match style + mood:** Ensure style and mood are compatible (use KG validation)
6. **Use object format for control:** Object format provides better control than strings
7. **Validate before generation:** Run `validate_json_prompt()` before submitting

---

## See Also

- `pipeline.md`: Complete generation pipeline documentation
- `install-guide.md`: ComfyUI installation
- KG engine: `scripts/engine/kg/engine.py` for skeleton and recommendation API