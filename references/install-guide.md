# ComfyUI + GGUF 模型安装指南

本指南从零开始，指导你完成 ComfyUI 的安装、GGUF 量化模型的下载，以及 image-gen 项目的配置。

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (推荐 Ubuntu 22.04+) / macOS (Apple Silicon) / Windows 10 |
| GPU | NVIDIA GPU (推荐 8GB+ 显存) 或 Apple Silicon (M1/M2/M3) |
| Python | 3.10+ |
| 磁盘空间 | 至少 20GB (ComfyUI + 模型) |
| 网络 | 需要访问 GitHub 和 HuggingFace，国内可以使用相关代理 |


## 1、安装 ComfyUI

### 1.1 克隆仓库

```bash
cd ~
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

> 💡 国内网络如果克隆慢，可以使用镜像加速：
> ```bash
> git clone https://gh-proxy.org/https://github.com/comfyanonymous/ComfyUI.git
> ```

### 1.2 创建 Python 虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 1.3 安装 PyTorch

**NVIDIA GPU (CUDA 12.1)：**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**NVIDIA GPU (CUDA 11.8)：**

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Apple Silicon (MPS)：**

```bash
pip install torch torchvision torchaudio
```

### 1.4 安装 ComfyUI 依赖

```bash
pip install -r requirements.txt
```

### 1.5 验证安装

```bash
python main.py --version
```

如果能正常输出版本号，说明安装成功。


## 2、下载模型

image-gen 使用 Comfy-Org 官方工作流作为基础，将主模型替换为 unsloth 量化版 GGUF 格式模型，体积小、推理快，适合消费级显卡。

项目提供两套工作流，按需选择：

| 工作流 | 主模型 (GGUF) | CLIP 文本编码器 | VAE | 特点 |
|--------|---------------|----------------|-----|------|
| ERNIE-Image | `ernie-image-Q8_0.gguf` | `ministral-3-3b.safetensors` | `flux2-vae.safetensors` | 百度出品，中文文字渲染强，适合海报、漫画 |
| Z-Image | `z-image-Q8_0.gguf` | `qwen_3_4b.safetensors` | `ae.safetensors` | 阿里出品，风格多样，美学表现优秀 |

> 💡 **工作流来源**：
> - ERNIE-Image 工作流基于 `Comfy-Org/ERNIE-Image`：https://hf-mirror.com/Comfy-Org/ERNIE-Image
> - Z-Image 工作流基于 `Comfy-Org/z_image`：https://hf-mirror.com/Comfy-Org/z_image
> - 主模型由 unsloth 提供 GGUF 量化版，采用 Unsloth Dynamic 2.0 方法，关键层上浮到更高精度。

### 2.1 下载 GGUF 主模型

unsloth 提供多种量化等级，推荐 **Q8_0**（几乎无损）或 **Q4_0**（省显存）：

**ERNIE-Image GGUF：**

```bash
cd ~/ComfyUI/models/unet

# Q8_0 量化（推荐，质量最佳）
huggingface-cli download unsloth/ERNIE-Image-GGUF \
  ernie-image-Q8_0.gguf \
  --local-dir .
```

**Z-Image GGUF：**

```bash
cd ~/ComfyUI/models/unet

# Q8_0 量化（推荐）
huggingface-cli download unsloth/Z-Image-GGUF \
  z-image-Q8_0.gguf \
  --local-dir .
```

> 💡 国内网络如果下载慢，使用 hf-mirror 镜像：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> # 下载 ERNIE-Image GGUF
> huggingface-cli download unsloth/ERNIE-Image-GGUF \
>   ernie-image-Q8_0.gguf \
>   --local-dir .
>
> # 下载 Z-Image GGUF
> huggingface-cli download unsloth/Z-Image-GGUF \
>   z-image-Q8_0.gguf \
>   --local-dir .
> ```

#### 其他可选量化等级

| 量化等级 | 文件大小 | 质量损失 | 推荐场景 |
|----------|----------|----------|----------|
| Q8_0 | ~原大小 80% | 几乎无损 | 显存充足，追求质量 |
| Q6_K | ~原大小 65% | 轻微 | 高质量省空间 |
| Q5_K_M | ~原大小 55% | 较小 | 平衡方案 |
| Q4_K_M | ~原大小 45% | 可接受 | 显存有限 |
| Q2_K | ~原大小 25% | 明显 | 仅测试用 |

### 2.2 下载 CLIP 文本编码器

两个工作流使用不同的 CLIP 模型：

**ERNIE-Image 使用 ministral-3-3b：**

```bash
cd ~/ComfyUI/models/clip

huggingface-cli download Comfy-Org/ERNIE-Image \
  text_encoders/ministral-3-3b.safetensors \
  --local-dir .
mv text_encoders/ministral-3-3b.safetensors .
rm -rf text_encoders
```

**Z-Image 使用 qwen_3_4b：**

```bash
cd ~/ComfyUI/models/clip

huggingface-cli download Comfy-Org/z_image \
  split_files/text_encoders/qwen_3_4b.safetensors \
  --local-dir .
mv split_files/text_encoders/qwen_3_4b.safetensors .
rm -rf split_files
```

### 2.3 下载 VAE 模型

**ERNIE-Image 使用 flux2-vae：**

```bash
cd ~/ComfyUI/models/vae

huggingface-cli download Comfy-Org/ERNIE-Image \
  vae/flux2-vae.safetensors \
  --local-dir .
mv vae/flux2-vae.safetensors .
rm -rf vae
```

**Z-Image 使用 ae（FLUX 系列通用 VAE）：**

```bash
cd ~/ComfyUI/models/vae

huggingface-cli download Comfy-Org/z_image \
  split_files/vae/ae.safetensors \
  --local-dir .
mv split_files/vae/ae.safetensors .
rm -rf split_files
```

### 2.4 验证模型文件

下载完成后，确认目录结构和文件完整：

```bash
# GGUF 主模型（二选一或全部下载）
ls -lh ~/ComfyUI/models/unet/ernie-image-Q8_0.gguf
ls -lh ~/ComfyUI/models/unet/z-image-Q8_0.gguf

# CLIP 文本编码器
ls -lh ~/ComfyUI/models/clip/ministral-3-3b.safetensors
ls -lh ~/ComfyUI/models/clip/qwen_3_4b.safetensors

# VAE
ls -lh ~/ComfyUI/models/vae/flux2-vae.safetensors
ls -lh ~/ComfyUI/models/vae/ae.safetensors
```

确保文件大小合理，没有损坏。

## 3、配置 ComfyUI 支持 GGUF

### 3.1 安装 GGUF 支持节点

ComfyUI 默认不支持 GGUF 模型，需要安装自定义节点：

```bash
cd ~/ComfyUI/custom_nodes

# 克隆 GGUF 支持节点
git clone https://github.com/city96/ComfyUI-GGUF.git

# 安装依赖
cd ComfyUI-GGUF
pip install -r requirements.txt
cd ../..
```

### 3.2 可选：安装 ComfyUI Manager（方便管理节点）

```bash
cd ~/ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
cd ../..
```

### 3.3 启动 ComfyUI

```bash
cd ~/ComfyUI
source venv/bin/activate
python main.py
```

启动后访问 `http://127.0.0.1:8188` 确认服务正常。

## 4、配置 image-gen

### 4.1 克隆 image-gen 项目

```bash
cd ~
git clone https://github.com/your-username/image-gen.git
cd image-gen
```

### 4.2 编辑配置文件

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
  "score_threshold": 8,
  "default_workflow": "workflows/ernie_image_gguf"
}
```

| 参数 | 说明 |
|------|------|
| `comfyui_host/port` | ComfyUI 服务地址 |
| `output_dir` | 生成图片保存目录 |
| `vision_api_url` | 视觉模型 API 地址（用于评估） |
| `vision_model` | 使用的视觉模型名称 |
| `vision_api_key` | API 密钥，建议通过环境变量 `VISION_API_KEY` 设置 |
| `max_iterations` | 最大迭代次数 |
| `score_threshold` | 质量阈值（1-10） |
| `default_workflow` | 默认工作流文件 |

### 4.3 设置 API 密钥（推荐）

```bash
export VISION_API_KEY="your-api-key-here"
```

## 5、测试运行

### 5.1 检查 ComfyUI 连接

```bash
python scripts/image-gen-cli.py check
```

如果显示连接成功，说明配置正确。

### 5.2 运行第一次生成

```bash
python scripts/image-gen.py "a cat sitting on a windowsill, watercolor style"
```

你会看到完整的 6 步流程输出：

```
=== Image Generation Pipeline ===
User intent: a cat sitting on a windowsill, watercolor style
Config: 127.0.0.1:8188

[Step 1] Intent Recognition (LLM)
  Seeds: ["subject:cat", "style:watercolor"]

[Step 2] KG Query
  Filled: ["subject", "style"]
  Recommendations: ["mood", "lighting", "color_palette"]

[Step 3] Prompt Generation
  Positive: a cat, watercolor style, warm mood, natural light...

[Step 4] ComfyUI Generation
  Connection OK
  Waiting for completion... (ID: xxx)

[Step 5] Evaluation
  Score: 8.2/8
  Passed threshold! Stopping.

[Step 6] KG Update
  KG updated with successful combination

=== SUCCESS ===
Best image: ~/image-gen-output/cli-run-001_20260429_102500_0.png
```

### 5.3 查看生成结果

```bash
ls -lh ~/image-gen-output/
```


## 6、常见问题

### Q1：ComfyUI 启动后浏览器访问不了

**检查防火墙：**

```bash
# Ubuntu/Debian
sudo ufw allow 8188/tcp

# 或者启动时指定监听地址
python main.py --listen 0.0.0.0 --port 8188
```

### Q2：模型下载太慢

**使用 hf-mirror 镜像：**

```bash
export HF_ENDPOINT=https://hf-mirror.com

# ERNIE-Image GGUF
huggingface-cli download unsloth/ERNIE-Image-GGUF ernie-image-Q8_0.gguf --local-dir .

# Z-Image GGUF
huggingface-cli download unsloth/Z-Image-GGUF z-image-Q8_0.gguf --local-dir .
```

### Q3：生成图片全黑或有噪点

可能原因：
1. 模型文件不完整，重新下载
2. 显存不足，使用 `--lowvram` 启动 ComfyUI
3. GGUF 量化等级太低，换 Q8_0 或 Q5_0

### Q4：评估环节报错

检查 `vision_api_url` 和 `vision_api_key` 是否配置正确。评估环节是可选的，如果暂时不用，可以将 `score_threshold` 设为 0 跳过。

### Q5：连续生成后质量下降

运行 `free-memory` 释放显存：

```bash
python scripts/image-gen-cli.py free-memory --unload
```

---

## 7、模型文件完整目录结构

安装完成后，你的 ComfyUI 目录应该类似这样：

```
~/ComfyUI/
├── models/
│   ├── unet/                         # GGUF 主模型（unsloth 量化版）
│   │   ├── ernie-image-Q8_0.gguf     #   ERNIE-Image（可选）
│   │   └── z-image-Q8_0.gguf         #   Z-Image（可选）
│   ├── clip/                         # CLIP 文本编码器
│   │   ├── ministral-3-3b.safetensors #   ERNIE-Image 使用
│   │   └── qwen_3_4b.safetensors      #   Z-Image 使用
│   ├── vae/                          # VAE 模型
│   │   ├── flux2-vae.safetensors      #   ERNIE-Image 使用
│   │   └── ae.safetensors             #   Z-Image 使用
│   ├── lora/                         # LoRA 适配器（可选）
│   └── controlnet/                   # ControlNet 模型（可选）
├── custom_nodes/
│   ├── ComfyUI-GGUF/                 # GGUF 支持节点（必需）
│   └── ComfyUI-Manager/              # 节点管理器（可选）
├── input/
├── output/
└── main.py
```

## 附录：GGUF 量化等级说明

unsloth 使用 Unsloth Dynamic 2.0 方法进行量化，关键层（attention、output 等）会自动上浮到更高精度，因此同等级量化下质量优于传统方法。

| 量化等级 | 文件大小 | 质量损失 | 推荐场景 |
|----------|----------|----------|----------|
| Q8_0 | ~原大小 80% | 几乎无损 | 显存充足，追求质量（推荐） |
| Q6_K | ~原大小 65% | 轻微 | 高质量，省空间 |
| Q5_K_M | ~原大小 55% | 较小 | 平衡方案 |
| Q4_K_M | ~原大小 45% | 可接受 | 显存有限 |
| Q2_K | ~原大小 25% | 明显 | 仅测试用 |

推荐：**Q8_0** 作为默认选择，质量几乎无损；显存不足时选择 **Q4_K_M**。
