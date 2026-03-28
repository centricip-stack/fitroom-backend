"""
GPU Memory Optimization Utilities for RunPod
Use these when running into VRAM limits on RTX 4090
"""

import torch
import os
from typing import Optional

class GPUMemoryManager:
    """Manage GPU memory for safe inference on limited VRAM"""
    
    @staticmethod
    def check_gpu_capability() -> dict:
        """Check available GPU resources"""
        if not torch.cuda.is_available():
            return {"available": False}
        
        return {
            "available": True,
            "device": torch.cuda.get_device_name(0),
            "total_memory_gb": torch.cuda.get_device_properties(0).total_memory / 1e9,
            "allocated_memory_gb": torch.cuda.memory_allocated(0) / 1e9,
            "cached_memory_gb": torch.cuda.memory_reserved(0) / 1e9,
        }
    
    @staticmethod
    def clear_cache():
        """Clear GPU cache to free memory"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    
    @staticmethod
    def log_memory():
        """Log current GPU memory usage"""
        if torch.cuda.is_available():
            print(f"GPU Memory Allocated: {torch.cuda.memory_allocated() / 1e9:.2f} GB")
            print(f"GPU Memory Cached: {torch.cuda.memory_reserved() / 1e9:.2f} GB")
    
    @staticmethod
    def setup_memory_efficient_mode():
        """Setup PyTorch for memory efficiency"""
        # Enable memory efficient attention (if available in torch >= 2.0)
        try:
            torch.set_float32_matmul_precision('medium')
        except:
            pass
        
        # Set up cache config
        os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512,expandable_segments:True'


def configure_inference_mode(device: Optional[str] = None, optimize_memory: bool = False):
    """
    Configure inference dtype and memory settings
    
    Args:
        device: 'cuda' or 'cpu'
        optimize_memory: Use fp16 instead of fp32/bf16
    
    Returns:
        torch.device, dtype
    """
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    torch_device = torch.device(device)
    
    if device == "cuda":
        # For RTX 4090: bf16 is optimal (unless memory constrained)
        if optimize_memory:
            dtype = torch.float16  # Saves ~50% memory
        elif torch.cuda.is_bf16_supported():
            dtype = torch.bfloat16  # Optimal for 4090
        else:
            dtype = torch.float32
    else:
        dtype = torch.float32
    
    return torch_device, dtype


# Example usage in routes.py:
"""
from app.services.gpu_memory_manager import GPUMemoryManager, configure_inference_mode

# In your FastAPI startup event
@app.on_event("startup")
async def startup_event():
    GPUMemoryManager.setup_memory_efficient_mode()
    gpu_info = GPUMemoryManager.check_gpu_capability()
    print(f"GPU Status: {gpu_info}")

# In your tryon endpoint
@router.post("/tryon")
async def tryon(...):
    GPUMemoryManager.clear_cache()  # Before inference
    # ... run inference ...
    GPUMemoryManager.clear_cache()  # After inference
    GPUMemoryManager.log_memory()   # Log for monitoring
"""
