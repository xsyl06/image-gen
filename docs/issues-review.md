# Image-Gen Skill 审查问题清单

**审查日期**: 2026-04-28  
**审查范围**: 完整代码库 + 配置 + 文档
**结果**：已经按照审查建议修改完成

---

## 🔴 安全问题

### 1. API Key 硬编码在 config.json

| 文件 | 行号 | 问题 |
|------|------|------|
| `scripts/engine/config.json` | L6 | `vision_api_key` 明文写入 `"sk-sp-59c981117a490d934b982d0097c0fd"` |

**风险**: API Key 随仓库公开或共享，可能导致额度被盗用。

**建议**:
- 先从配置文件获取，如果没有，改为从环境变量读取：`os.environ.get("VISION_API_KEY")`

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

### 5. config.json 结构与代码读取方式不匹配

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

**建议**: 
1. 阅读当前代码，检查视觉模型部分获取的是扁平结构还是字典结构，如果是字典结构，修改代码适配当前 config 结构（读 `cfg["vision_api_url"]` 和 `cfg["vision_api_key"]`）

---

## 🟡 逻辑问题

### 6. Prompt 改进策略过于粗糙

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

### 7. KG 翻译存在竞态风险

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

### 8. 评估 Fallback 阈值设置不合理

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

### 9. 缺少 README.md

仓库根目录没有 `README.md`，只有面向 Agent 的 `SKILL.md` 和 `CLAUDE.md`。

**建议**: 添加项目级 README，包含：
- 项目简介
- 快速上手（安装 + 首次运行）
- 目录结构
- 依赖说明

---

### 10. KG 实体缺少中文名称

| 文件 | 问题 |
|------|------|
| `scripts/engine/kg/data/prompt_graph.json` | 大量实体 `name_zh` 字段为空或缺失 |

**影响**: LLM 意图识别时的 catalog preview 包含中文提示（`tag (中文)`），缺失会降低中文输入的提取准确率。
