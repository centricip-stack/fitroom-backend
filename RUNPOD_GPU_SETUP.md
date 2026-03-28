# FasthuVTON 1.5 → RunPod GPU Integration Guide

## Overview
Your FasthuVTON backend is now configured for GPU. The RTX 4090 on RunPod will provide **~100x speedup** vs CPU.

---

## Part 1: RunPod Setup

### Step 1: Create RunPod Pod with Correct Image
1. Go to [RunPod Secure Cloud](https://www.runpod.io/console/pods)
2. Click **"Rent GPU"**
3. Select **RTX 4090**
4. Choose a base image: **PyTorch 2.0+ with CUDA 12+** (e.g., `pytorch/pytorch:2.0-cuda11.8-runtime-ubuntu20.04`)
5. Allocate resources:
   - **GPU**: 1× RTX 4090
   - **vCPU**: 4-8 cores
   - **RAM**: 16-32GB
   - **Storage**: 50GB SSD (for model weights + cache)
   - **Disk Volume**: 20GB (scratch space for outputs)

### Step 2: SSH into RunPod
```bash
ssh root@your-runpod-ip -p 22
```

### Step 3: Clone & Setup Backend
```bash
cd /workspace
git clone <your-repo-url> fashn-vton-1.5
cd fashn-vton-1.5

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e . --no-build-isolation
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Step 4: Copy .env.runpod
```bash
cp .env.runpod .env
```

### Step 5: Download Model Weights
```bash
python scripts/download_weights.py
# Or: wget https://[your-weights-url] -O app/weights/model.safetensors
```

### Step 6: Start Server
```bash
# Make sure TRYON_DEVICE=cuda is set
export TRYON_DEVICE=cuda
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Part 2: Resource Limiting (IMPORTANT!)

### Memory Management
To prevent GPU memory overflow on your limited RunPod account:

#### Option A: Automatic Memory Management (Recommended)
The `.env.runpod` already includes:
```bash
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```
This limits GPU memory fragmentation.

#### Option B: Per-Request Memory Limit (in routes.py)
Add this to automatically clear cache between requests (edit [app/api/routes.py](app/api/routes.py#L20)):

```python
@router.post("/tryon", response_model=TryOnResponse)
async def tryon(person_image: UploadFile = File(...), garment_image: UploadFile = File(...), category: str = Form(...)):
    import torch
    
    # Clear GPU cache before inference
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    service = get_service()
    person = Image.open(BytesIO(await person_image.read())).convert("RGB")
    garment = Image.open(BytesIO(await garment_image.read())).convert("RGB")
    output_path = service.run(person, garment, category)
    
    # Clear GPU cache after inference
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    
    return TryOnResponse(output_image_path=output_path)
```

### Monitor GPU Usage
```bash
# SSH into RunPod and monitor
watch -n 1 nvidia-smi

# Expected on RTX 4090: ~20-24GB used per inference, ~5-10s per try-on
```

---

## Part 3: From Local Dev to RunPod

### Option 1: Use RunPod as External Service (Recommended)
Keep your local backend as-is. Create a separate RunPod deployment:

**Local Backend** → REST API calls to **RunPod GPU Backend**

Create a new route in RunPod:
```python
# In RunPod deployment's routes.py
@router.post("/tryon")
async def tryon_gpu(...):
    # Same as local, but with TRYON_DEVICE=cuda enforced
    pass
```

### Option 2: Replace Local with RunPod (Full Migration)
Deploy your **entire** backend to RunPod and disable local version.

---

## Part 4: Deployment Strategies

### Strategy A: RunPod + Systemd (24/7 Server)
1. Create systemd service `/etc/systemd/system/tryon-api.service`:
```ini
[Unit]
Description=FasthuVTON GPU API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/workspace/fashn-vton-1.5
Environment="PATH=/workspace/fashn-vton-1.5/.venv/bin"
Environment="TRYON_DEVICE=cuda"
Environment="PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512"
ExecStart=/workspace/fashn-vton-1.5/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable & start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable tryon-api
sudo systemctl start tryon-api
sudo systemctl status tryon-api
```

### Strategy B: RunPod API Endpoint (Serverless)
RunPod offers HTTP endpoint support - your app auto-scales down when idle.

---

## Part 5: Performance Expectations

| Metric | CPU | RTX 4090 (GPU) |
|--------|-----|----------------|
| Inference Time | 2-3 min | 5-10 sec |
| Memory Used | 32GB RAM | 20-24GB VRAM |
| Startup Time | N/A | ~30 sec (model load) |
| Cost/Hour | $0/local | ~$0.44 on RunPod |
| Speedup | 1× | **~15-20×** |

---

## Part 6: Troubleshooting

### Issue: "CUDA out of memory"
**Solution:**
```bash
# Reduce to fp16 inference (half precision)
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:256
# Or explicitly limit in code:
# in pipeline.py: self.inference_dtype = torch.float16
```

### Issue: "No module named 'torch'"
**Solution:**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### Issue: GPU not detected
**Solution:**
```bash
nvidia-smi  # Check if driver is installed
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: Model weights not found
**Solution:**
```bash
ls -la app/weights/
# Check model.safetensors exists and dwpose/ folder populated
```

---

## Part 7: API Usage (Same on Local & RunPod)

### Test the endpoint:
```bash
curl -X POST "http://your-runpod-ip:8000/tryon" \
  -F "person_image=@person.jpg" \
  -F "garment_image=@garment.jpg" \
  -F "category=tops"
```

### Response:
```json
{
  "output_image_path": "outputs/output.png"
}
```

---

## Summary Checklist

- [ ] Update code (Pipeline + Routes) ✅ DONE
- [ ] Create RunPod pod with RTX 4090
- [ ] SSH and clone/setup backend
- [ ] Copy `.env.runpod` → `.env`
- [ ] Test with `nvidia-smi`
- [ ] Run: `export TRYON_DEVICE=cuda && uvicorn app.main:app --host 0.0.0.0 --port 8000`
- [ ] Test endpoints with sample images
- [ ] Monitor GPU with `watch nvidia-smi`
- [ ] Setup systemd service for persistence

---

**Questions?** Check RunPod docs or test locally first with `TRYON_DEVICE=cpu` to verify API works.
