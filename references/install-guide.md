# ComfyUI Installation Guide

This guide covers installing and configuring ComfyUI for the image-gen skill on Linux (CUDA) and macOS (MPS) platforms.

---

## Linux (CUDA)

### Prerequisites
- NVIDIA GPU with CUDA support
- Python 3.10+ installed
- CUDA toolkit (11.8+ recommended)

### 1. Install Dependencies

**System packages:**
```bash
sudo apt update
sudo apt install -y python3-pip git wget
```

**CUDA verification:**
```bash
nvidia-smi  # Check GPU and CUDA driver version
```

### 2. Clone ComfyUI

```bash
cd ~
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

### 3. Install Python Dependencies

**Create virtual environment (recommended):**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Install packages:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

**Alternative: Use pre-built PyTorch with CUDA 12.1:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

### 4. Download Models

**ERNIE-Image (Recommended for Chinese users):**
```bash
cd models/checkpoints
wget https://huggingface.co/BAAI/ERNIE-Image/resolve/main/ernie_image_v1.0.safetensors
```

**Qwen-Image:**
```bash
wget https://huggingface.co/Qwen/Qwen-Image/resolve/main/qwen_image_v1.0.safetensors
```

**FLUX.1-dev (Alternative):**
```bash
wget https://huggingface.co/black-forest-labs/FLUX.1-dev/resolve/main/flux1-dev.safetensors
```

**Stable Diffusion 1.5 (Classic):**
```bash
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
```

**Model directory structure:**
```
ComfyUI/models/
├── checkpoints/        # Main model weights
├── lora/               # LoRA adapters
├── vae/                # VAE models
├── clip/               # CLIP models
└── controlnet/         # ControlNet models
```

### 5. Start ComfyUI

**Basic startup:**
```bash
python main.py
```

**Custom port:**
```bash
python main.py --port 8188
```

**Listen on all interfaces (for remote access):**
```bash
python main.py --listen 0.0.0.0 --port 8188
```

**Low VRAM mode (for GPUs with <8GB):**
```bash
python main.py --lowvram
```

**CPU mode (no GPU):**
```bash
python main.py --cpu
```

---

## macOS (MPS)

### Prerequisites
- macOS 12.3+ (Monterey or later)
- Apple Silicon Mac (M1/M2/M3) or Intel Mac with supported GPU
- Python 3.10+ installed
- Xcode Command Line Tools

### 1. Install Dependencies

**Homebrew packages:**
```bash
brew install python@3.10 git wget
```

**Xcode tools:**
```bash
xcode-select --install
```

### 2. Clone ComfyUI

```bash
cd ~
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

### 3. Install Python Dependencies

**Create virtual environment:**
```bash
python3.10 -m venv venv
source venv/bin/activate
```

**Install PyTorch with MPS support:**
```bash
pip install torch torchvision torchaudio
pip install -r requirements.txt
```

**Note:** MPS (Metal Performance Shaders) acceleration is automatically enabled on Apple Silicon.

### 4. Download Models

**Same models as Linux section. Use smaller models for better performance on macOS:**

**Recommended: SD 1.5 or SDXL Turbo:**
```bash
cd models/checkpoints
wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors
```

**SDXL Turbo (fast generation):**
```bash
wget https://huggingface.co/stabilityai/sdxl-turbo/resolve/main/sd_xl_base_1.0.safetensors
```

### 5. Start ComfyUI

**Basic startup (MPS auto-detected):**
```bash
python main.py
```

**Force MPS device:**
```bash
python main.py --device mps
```

**Fallback to CPU (if MPS issues):**
```bash
python main.py --cpu
```

---

## Windows (CUDA)

### Prerequisites
- Windows 10/11
- NVIDIA GPU with CUDA support
- Python 3.10+ (from python.org)

### Quick Install

**1. Install Git and Python:**
- Download from: https://git-scm.com/download/win
- Download from: https://www.python.org/downloads/

**2. Clone ComfyUI:**
```powershell
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

**3. Install dependencies:**
```powershell
python -m venv venv
venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

**4. Download models (same as Linux section)**

**5. Start:**
```powershell
python main.py
```

---

## Model Recommendations

### For Different Use Cases

**High Quality (slow):**
- FLUX.1-dev (12B parameters, excellent quality)
- Stable Diffusion XL (SDXL)

**Balanced Quality/Speed:**
- ERNIE-Image (good for Chinese content)
- Stable Diffusion 1.5 (classic, well-supported)

**Fast Generation:**
- SDXL Turbo (1-step generation)
- LCM-LoRA + SD 1.5 (4-step generation)

### Model Sources

**HuggingFace (recommended):**
- https://huggingface.co/models?pipeline_tag=text-to-image

**Civitai (community models):**
- https://civitai.com/

**ModelScope (Chinese models):**
- https://modelscope.cn/models

---

## Verify Installation

### Check Server Status

**HTTP endpoint:**
```bash
curl http://127.0.0.1:8188/system_stats
```

**Expected response:**
```json
{
  "system": {
    "devices": [
      {
        "name": "NVIDIA GeForce RTX 3080",
        "type": "cuda",
        "vram_total": 10737418240
      }
    ]
  }
}
```

### Test Generation

**Python test:**
```python
from comfyui import check_connection, generate_image

cfg = {
    "comfyui_host": "127.0.0.1",
    "comfyui_port": 8188,
    "output_dir": "~/test-output"
}

if check_connection(cfg):
    print("✓ ComfyUI connection successful")
else:
    print("✗ ComfyUI not reachable")
```

### Browser Interface

Open in browser:
```
http://127.0.0.1:8188
```

You should see the ComfyUI graph interface. Try loading a basic workflow and generating a test image.

---

## Troubleshooting

### Common Issues

**1. Connection Refused:**
```
Error: Cannot connect to ComfyUI at http://127.0.0.1:8188
```
**Solution:** Ensure ComfyUI is running: `python main.py --port 8188`

**2. CUDA Out of Memory:**
```
RuntimeError: CUDA out of memory
```
**Solution:** Use `--lowvram` mode or reduce image resolution in workflow

**3. MPS Not Detected (macOS):**
```
Warning: MPS not available, falling back to CPU
```
**Solution:** Update macOS to 12.3+ or use `python main.py --cpu`

**4. Model Loading Error:**
```
FileNotFoundError: model.safetensors not found
```
**Solution:** Verify model file exists in `models/checkpoints/`

**5. Python Version Conflict:**
```
ModuleNotFoundError: No module named 'torch'
```
**Solution:** Use Python 3.10+ and reinstall dependencies

---

## ComfyUI Manager (Optional)

For easier workflow and model management:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/ltdrdata/ComfyUI-Manager.git
```

Restart ComfyUI and access Manager via browser interface.

---

## Next Steps

After successful installation:

1. Configure image-gen skill: Edit `scripts/engine/config.json` with your ComfyUI settings
2. Load a workflow template: Use default or custom ComfyUI workflows
3. Test generation: Run `/img "test prompt"` to verify pipeline
4. Explore models: Download additional models based on your needs

---

## See Also

- `pipeline.md`: Image generation pipeline documentation
- `prompt-schema.md`: JSON prompt schema details
- ComfyUI docs: https://github.com/comfyanonymous/ComfyUI