<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&text=image-gen&fontSize=50&fontAlignY=35&desc=AI%20%E5%9B%BE%E5%83%8F%E7%94%9F%E6%88%90%E6%B5%81%E6%B0%B4%E7%BA%BF&descAlignY=55&fontColor=ffffff" width="100%" />

[English](../README.md) | [中文](README.zh-CN.md)

</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-blue?style=flat&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/依赖-零依赖-brightgreen?style=flat" alt="零依赖" />
  <img src="https://img.shields.io/badge/ComfyUI-必需-orange?style=flat" alt="ComfyUI" />
</p>
<p align="center">
  <img src="https://skillicons.dev/icons?i=python,git,github&theme=dark" alt="技术栈" />
</p>

---

> 将自然语言转化为高质量图像 —— 基于提示词知识图谱与多模态视觉评估的六步 AI 生成流水线。

**image-gen** 是一个端到端的图像生成引擎。只需一段文字描述，即可生成经过迭代优化的高质量图像。系统通过知识图谱丰富提示词，提交 ComfyUI 进行生成，并使用多模态视觉模型进行质量评估，不达阈值则自动优化重试。

---

## 核心特性

<table>
<tr>
<td width="50%" valign="top">

### 结构化提示词
14 维度 JSON 提示词架构，覆盖主体、风格、氛围、构图、光影、色彩等维度，实现对生成效果的精细控制。

</td>
<td width="50%" valign="top">

### 提示词知识图谱
基于共现统计的实体推荐系统，根据种子关键词自动推荐风格、氛围、光影等互补属性。

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 迭代优化
视觉模型从 6 个维度（主体准确度、风格保真度、氛围、构图、技术质量、整体满意度）打分，反馈改进后的提示词，自动重试直到达标。

</td>
<td width="50%" valign="top">

### 零外部依赖
核心引擎全部使用 Python 标准库实现（`urllib`、`json`、`pathlib`），无需 `pip install`。

</td>
</tr>
</table>

---

## 流水线

```
自然语言描述
       │
       ▼
┌─────────────────┐
│ 1. 意图识别      │  ── 提取种子实体
│                 │    （LLM + 关键词回退）
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. 知识图谱查询  │  ── 通过共现统计推荐
│    (Skeleton)   │    互补实体
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. 提示词生成    │  ── 组装 14 维 JSON 提示词
│                 │    → 转换为文本格式
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. ComfyUI 生成  │  ── 提交工作流、轮询状态
│                 │    下载生成图像
└────────┬────────┘
         ▼
┌─────────────────┐
│ 5. 评估循环      │  ── 视觉模型 6 维度打分
│                 │    未达标 → 优化提示词重试
└────────┬────────┘
         ▼
┌─────────────────┐
│ 6. 经验积累      │  ── 将成功的实体组合
│                 │    写回知识图谱
└─────────────────┘
```

---

## 快速开始

### 安装为 Claude Code 技能（推荐）

本项目是一个 **Claude Code 技能** —— 安装后，Claude 可以通过自然语言对话驱动完整的图像生成流水线。

**全局安装**（所有 Claude Code 会话中可用）：

```bash
# 1. 克隆仓库
git clone git@github.com:xsyl06/image-gen.git

# 2. 将技能目录复制到 ~/.claude/skills/
cp -r image-gen/image-gen ~/.claude/skills/image-gen

# 3. （可选）如已有 ComfyUI 工作流，可软链接或复制：
#    cp -r /path/to/your/workflows ~/.claude/skills/image-gen/scripts/engine/workflows/

# 4. 编辑 config.json 配置 ComfyUI 和视觉模型 API：
cd ~/.claude/skills/image-gen
# 编辑 scripts/engine/config.json（详见下方"配置"章节）
```

安装后重启 Claude Code 即可自动生效。直接用自然语言描述你想生成的图像：

```
用户: 生成一张赛博朋克风格的城市夜景
用户: 画一只水彩风格的猫在读书
```

**项目内安装**（仅在本仓库目录下生效）：

```bash
git clone git@github.com:xsyl06/image-gen.git
cd image-gen
# 项目根目录的 SKILL.md 会在 Claude Code 打开本仓库时自动激活技能
```

---

### 环境要求

- **Python 3.8+** —— 无需安装任何第三方包
- **ComfyUI** 运行于 `127.0.0.1:8188`（[安装指南](../references/install-guide.md)）
- 兼容 OpenAI API 的视觉/对话模型（用于意图识别和图像评估）

### 配置

编辑 `scripts/engine/config.json`：

```json
{
  "comfyui_host": "127.0.0.1",
  "comfyui_port": 8188,
  "output_dir": "~/image-gen-output",
  "vision_api_url": "https://your-api-endpoint/v1",
  "vision_model": "qwen3.6-plus",
  "vision_api_key": "",
  "max_iterations": 3,
  "score_threshold": 8
}
```

> **安全提示**：建议将 `VISION_API_KEY` 设置为环境变量，而非写入 config.json 文件。

### 运行

```bash
python scripts/image-gen.py "一只猫在读书"

# 自定义参数
python scripts/image-gen.py "一只猫" --iterations 5 --threshold 9
python scripts/image-gen.py "一只猫" --config custom.json
```

---

## 项目结构

```
image-gen/
├── scripts/
│   ├── image-gen.py              # CLI 入口
│   └── engine/
│       ├── intent.py             # LLM 意图识别 + 关键词回退
│       ├── kg/
│       │   ├── engine.py         # PromptKG —— 知识图谱引擎
│       │   └── data/             # 实体定义 & 共现数据
│       ├── json_prompt.py        # 14 维 JSON 提示词架构
│       ├── prompt_assembly.py    # 从 KG skeleton 组装提示词
│       ├── comfyui.py            # ComfyUI HTTP 客户端（提交/轮询/下载）
│       ├── evaluator.py          # 视觉模型 6 维度图像评估
│       ├── workflow_loader.py    # 工作流模板加载 & 参数注入
│       ├── kg_update.py          # 经验写回知识图谱
│       ├── config.json           # 配置文件
│       └── workflows/            # ComfyUI 工作流模板
├── references/                   # 文档
└── output/                       # 生成的图像
```

---

## 核心模块

| 模块 | 职责 |
|------|------|
| `intent.py` | 将自然语言解析为 KG 种子实体（LLM 或关键词回退） |
| `kg/engine.py` | 知识图谱 —— 基于共现统计的实体推荐 |
| `json_prompt.py` | 14 维结构化提示词架构及文本转换 |
| `prompt_assembly.py` | 从 KG skeleton 和用户意图组装完整提示词 |
| `comfyui.py` | ComfyUI HTTP 客户端 —— 提交工作流、轮询状态、下载图像 |
| `evaluator.py` | 视觉模型 6 维加权评估 |
| `workflow_loader.py` | 加载和配置 ComfyUI 工作流模板 |
| `kg_update.py` | 将成功的提示词-实体组合写回知识图谱 |

---

## 文档

| 文档 | 说明 |
|------|------|
| [流水线](../references/pipeline.md) | 完整 6 步流水线详解 |
| [提示词架构](../references/prompt-schema.md) | 14 维 JSON 提示词规范 |
| [安装指南](../references/install-guide.md) | ComfyUI 安装说明 |

---

## 架构特点

- **零外部依赖** —— 所有模块仅使用 Python 标准库
- **知识图谱** —— 基于 JSON 的实体定义与共现统计，实现智能提示词增强
- **结构化提示词** —— 14 维架构（主体、风格、氛围、构图、光影、背景、色彩、质量标签、宽高比、分辨率、负面提示词、权重强调、中文排版 DSL、对抗式构图）
- **视觉模型评估** —— 6 维加权打分 + 迭代提示词优化
- **ComfyUI 集成** —— 基于 HTTP 的工作流提交、轮询和图像下载
- **中文排版支持** —— 内置中文文字排版 DSL，适用于海报/排版类图像生成

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%" />

</div>
