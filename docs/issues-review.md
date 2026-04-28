# Image-Gen Skill 审查问题清单

**审查日期**: 2026-04-28  
**审查范围**: 完整代码库 + 配置 + 文档

---

## 🔴 安全问题

### 1. API Key 硬编码在 config.json

| 文件 | 行号 | 问题 |
|------|------|------|
| `scripts/engine/config.json` | L6 | `vision_api_key` 明文写入 `"sk-sp-59c981117a490d934b982d0097c0fd"` |

**风险**: API Key 随仓库公开或共享，可能导致额度被盗用。

**建议**:
- 从 `config.json` 中删除 `vision_api_key` 字段
- 改为从环境变量读取：`os.environ.get("VISION_API_KEY")`
- 或将 API Key 移到 `~/.image-gen/config.json` 等用户级配置文件中
- 在 `.gitignore` 中排除敏感配置文件

---

### 2. .gitignore 覆盖不全

| 文件 | 问题 |
|------|------|
| `.gitignore` | 仅包含 `engine/__pycache__`，遗漏大量应忽略的文件 |

**当前内容**:
```
engine/__pycache__
```

**建议补充**:
```
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/

# 生成图片
output/

# 敏感配置
config.local.json
.env
*.key

# 操作系统
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Claude Code 本地设置
.claude/settings.local.json
```

---

### 3. 生成图片被提交到仓库

| 目录 | 问题 |
|------|------|
| `output/` | 包含 2 张生成图片，共 ~3MB，不应纳入版本控制 |

**文件**:
- `output/pipeline-002_20260427_221852_0.png` (1.5MB)
- `output/pipeline-002_20260427_224253_0.png` (1.6MB)

**建议**: 将 `output/` 加入 `.gitignore`，用 `git rm --cached output/*.png` 清理。

---

### 4. .claude/settings.local.json 含开发机本地路径

| 文件 | 问题 |
|------|------|
| `.claude/settings.local.json` | 包含 Windows 路径 `e:/python/workspace/image-gen/...` |

**建议**: 将 `.claude/settings.local.json` 加入 `.gitignore`。

---

## 🟡 配置与一致性问题

### 5. 默认 workflow 名称不一致

| 位置 | 声明的默认值 |
|------|------------|
| `scripts/engine/config.json` | `"workflows/image_z_image_gguf.json"` |
| `SKILL.md` 文档 Step 4c | `ernie_image_gguf.json` |
| `scripts/image-gen-cli.py` cmd_pipeline | `workflows/ernie_image_gguf.json` |

**实际文件**: 仓库中两个 workflow 都存在：
- `scripts/engine/workflows/ernie_image_gguf.json` (9.2KB)
- `scripts/engine/workflows/image_z_image_gguf.json` (3KB)

**影响**: 不同入口使用的默认 workflow 不同，可能导致出图效果不一致。

**建议**: 统一默认 workflow 名称，并在文档中保持一致。

---

### 6. vision_model 不是视觉模型

| 文件 | 值 | 问题 |
|------|----|------|
| `config.json` | `"qwen3.6-plus"` | 这是语言模型，不具备图像理解能力 |

**影响**: 评估环节（evaluate）和图片描述（describe）使用语言模型无法真正"看"图片，评估质量受限。

**建议**: 换用视觉模型，如 `qwen-vl-max`、`qwen2.5-vl-72b-instruct` 等支持图像输入的模型。

---

### 7. config.json 结构与代码读取方式不匹配

`intent.py` 中的 `_call_chat_api` 读取配置：
```python
vision_cfg = cfg.get("vision_model", {})  # 期望是字典
base_url = vision_cfg.get("base_url", "")  # 从字典读
model = vision_cfg.get("model", "qwen3.6-plus")
api_key = vision_cfg.get("api_key_env", "")
```

但 `config.json` 的结构是扁平的：
```json
{
  "vision_model": "qwen3.6-plus",        // 字符串，不是字典
  "vision_api_url": "https://...",       // API URL 在顶层
  "vision_api_key": "sk-..."              // API Key 在顶层
}
```

**影响**: `base_url` 始终为空字符串，`_call_chat_api` 会抛出 `ValueError: No chat API configured`。

**建议**: 二选一：
1. 修改代码适配当前 config 结构（读 `cfg["vision_api_url"]` 和 `cfg["vision_api_key"]`）
2. 或修改 config.json 为嵌套结构：`{ "vision_model": { "base_url": "...", "model": "...", "api_key_env": "..." } }`

---

## 🟡 逻辑问题

### 8. Prompt 改进策略过于粗糙

| 文件 | 位置 | 问题 |
|------|------|------|
| `scripts/image-gen.py` | L120 | `current_prompt["subject"] = improved_text` |
| `scripts/engine/evaluator.py` | `_refine_prompt()` | 同样只替换 subject 字段 |

**问题**: Vision 模型返回的 `improved_prompt` 通常是一个完整的自然语言描述（如 "A fluffy orange cat sitting on a wooden windowsill with soft morning light"），直接替换 `subject` 字段会导致：
- 丢失原有的 style、mood、composition 等维度
- 下一次生成变成纯文本 subject，不再使用 KG 推荐

**建议**: 
- 将 `improved_prompt` 解析回结构化字段，或用 LLM 提取改进点
- 或者将 `improved_prompt` 作为 `subject.details` 追加而非覆盖

---

### 9. KG 翻译存在竞态风险

| 文件 | 问题 |
|------|------|
| `scripts/engine/kg_update.py` | 用 `subprocess.Popen` 启动后台翻译进程，多个进程同时修改 `prompt_graph.json` |

**问题**: 
1. 第一次出图成功 → 触发翻译进程 A（读写 prompt_graph.json）
2. 几秒后再次出图 → 触发翻译进程 B（也读写 prompt_graph.json）
3. 两个进程可能互相覆盖写入

**建议**: 
- 使用文件锁（`fcntl.flock`）保护读写
- 或改为同步翻译（牺牲一点速度但更安全）
- 或使用临时文件 + 原子重命名

---

### 10. 评估 Fallback 阈值设置不合理

| 文件 | 问题 |
|------|------|
| `scripts/engine/evaluator.py` | Vision API 不可达时返回全 5 分 |

**当前逻辑**:
```python
# 全部维度给默认 5 分
"weighted_score": 5.0,
```

默认阈值是 8 分，5 分 < 8 分 → 判定为未达标 → 尝试改进 → 但改进后生成的图片可能实际上很好。

**问题**: 如果 Vision API 一直不可用（比如网络问题），所有生成都会被错误标记为"不达标"。

**建议**: 
- API 不可达时返回 `None` 或特殊标记，让调用方决定是否跳过评估
- 或提供 `--skip-eval` 选项

---

## 🟢 小问题

### 11. 缺少 README.md

仓库根目录没有 `README.md`，只有面向 Agent 的 `SKILL.md` 和 `CLAUDE.md`。

**建议**: 添加项目级 README，包含：
- 项目简介
- 快速上手（安装 + 首次运行）
- 目录结构
- 依赖说明

---

### 12. KG 实体缺少中文名称

| 文件 | 问题 |
|------|------|
| `scripts/engine/kg/data/prompt_graph.json` | 大量实体 `name_zh` 字段为空或缺失 |

**影响**: LLM 意图识别时的 catalog preview 包含中文提示（`tag (中文)`），缺失会降低中文输入的提取准确率。

---

### 13. evals/evals.json 无实际测试文件

| 文件 | 问题 |
|------|------|
| `evals/evals.json` | 6 个测试用例的 `"files": []` 全为空 |

**影响**: 评估用例只有预期描述，没有实际运行结果，无法验证功能回归。

---

## 📊 问题汇总

| 级别 | 数量 | 关键词 |
|------|------|--------|
| 🔴 安全 | 4 | API Key 泄露、gitignore、敏感文件 |
| 🟡 配置 | 3 | workflow 不一致、模型类型错误、配置结构不匹配 |
| 🟡 逻辑 | 3 | prompt 改进粗糙、竞态风险、评估 fallback |
| 🟢 小问题 | 3 | 缺少 README、中文缺失、测试文件缺失 |

---

_由 奥龙 🐉 自动审查生成_
