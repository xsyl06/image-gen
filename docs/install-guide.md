# ComfyUI + GGUF 模型安装指南

本指南从零开始，指导你完成 ComfyUI 的安装、GGUF 量化模型的下载，以及 image-gen 项目的配置。

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Linux (推荐 Ubuntu 22.04+) / macOS (Apple Silicon) |
| GPU | NVIDIA GPU (推荐 8GB+ 显存) 或 Apple Silicon (M1/M2/M3) |
| Python | 3.10+ |
| 磁盘空间 | 至少 20GB (ComfyUI + 模型) |
| 网络 | 需要访问 GitHub 和 HuggingFace |

---

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

---

## 2、下载 GGUF 量化模型

image-gen 默认使用 GGUF 格式的量化模型，这类模型体积小、推理快，适合消费级显卡。

### 2.1 推荐模型

| 模型 | 用途 | 大小 | 下载链接 |
|------|------|------|----------|
| [Flux.1-Dev-GGUF](https://huggingface.co/city96/FLUX.1-dev-gguf) | 高质量通用 | ~12GB | 推荐 Q4_0 量化 |
| [Stable Diffusion 1.5 GGUF](https://huggingface.co/city96/stable-diffusion-v1-5-gguf) | 快速出图 | ~2GB | 推荐 Q8_0 量化 |
| [ERNIE-Image](https://huggingface.co/BAAI/ERNIE-Image) | 中文场景 | ~4GB | 中文文字渲染好 |

### 2.2 下载模型（以 Flux.1-Dev 为例）

```bash
cd ~/ComfyUI/models/unet

# 使用 huggingface-cli（需要先安装 pip install huggingface-hub）
huggingface-cli download city96/FLUX.1-dev-gguf \
  flux1-dev-Q4_0.gguf \
  --local-dir .

# 或者直接用 wget 下载
wget https://huggingface.co/city96/FLUX.1-dev-gguf/resolve/main/flux1-dev-Q4_0.gguf
```

> 💡 国内网络如果下载慢：
> ```bash
> # 使用 hf-mirror 镜像
> export HF_ENDPOINT=https://hf-mirror.com
> huggingface-cli download city96/FLUX.1-dev-gguf \
>   flux1-dev-Q4_0.gguf \
>   --local-dir .
> ```

### 2.3 下载 CLIP 模型（Flux 需要）

```bash
cd ~/ComfyUI/models/clip

# Flux 需要两个 CLIP 模型
huggingface-cli download comfyanonymous/flux_text_encoders \
  clip_l.safetensors t5xxl_fp8_e4m3fn.safetensors \
  --local-dir .

# 或使用 hf-mirror
HF_ENDPOINT=https://hf-mirror.com huggingface-cli download comfyanonymous/flux_text_encoders \
  clip_l.safetensors t5xxl_fp8_e4m3fn.safetensors \
  --local-dir .
```

### 2.4 下载 VAE 模型

```bash
cd ~/ComfyUI/models/vae

wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors

# 或 hf-mirror
HF_ENDPOINT=https://hf-mirror.com wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/ae.safetensors
```

### 2.5 验证模型文件

```bash
ls -lh ~/ComfyUI/models/unet/
ls -lh ~/ComfyUI/models/clip/
ls -lh ~/ComfyUI/models/vae/
```

确保模型文件完整（大小合理，没有损坏）。

---

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

---

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
  "default_workflow": "workflows/ernie_image_gguf.json"
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

---

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

---

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

**使用 hf-mirror：**

```bash
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download city96/FLUX.1-dev-gguf flux1-dev-Q4_0.gguf --local-dir .
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
│   ├── unet/                    # GGUF 量化模型
│   │   └── flux1-dev-Q4_0.gguf
│   ├── clip/                    # CLIP 文本编码器
│   │   ├── clip_l.safetensors
│   │   └── t5xxl_fp8_e4m3fn.safetensors
│   ├── vae/                     # VAE 模型
│   │   └── ae.safetensors
│   ├── lora/                    # LoRA 适配器（可选）
│   └── controlnet/              # ControlNet 模型（可选）
├── custom_nodes/
│   ├── ComfyUI-GGUF/            # GGUF 支持节点
│   └── ComfyUI-Manager/         # 节点管理器（可选）
├── input/
├── output/
└── main.py
```

---

## 8、性能参考

| 硬件配置 | 模型 | 分辨率 | 单张耗时 |
|----------|------|--------|----------|
| RTX 4090 (24GB) | Flux.1-Dev Q4_0 | 1024×1024 | ~15s |
| RTX 3090 (24GB) | Flux.1-Dev Q4_0 | 1024×1024 | ~25s |
| RTX 4060 (8GB) | SD1.5 Q8_0 | 512×512 | ~5s |
| M2 Max (32GB) | Flux.1-Dev Q4_0 | 1024×1024 | ~60s |

---

## 附录：GGUF 量化等级说明

| 量化等级 | 文件大小 | 质量损失 | 推荐场景 |
|----------|----------|----------|----------|
| Q8_0 | ~原大小 80% | 几乎无损 | 显存充足，追求质量 |
| Q5_0 | ~原大小 50% | 轻微 | 平衡方案 |
| Q4_0 | ~原大小 40% | 可接受 | 显存有限 |
| Q2_K | ~原大小 25% | 明显 | 仅测试用 |

推荐：**Q4_0** 作为默认选择，在质量和速度之间取得较好平衡。
