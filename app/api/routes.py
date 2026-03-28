from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
from io import BytesIO
import os
from app.models.schemas import TryOnResponse
from app.core.pipeline import FashnVTONService
# NEW: Import your memory manager
from app.services.gpu_memory_manager import configure_inference_mode, GPUMemoryManager

router = APIRouter()
_service = None

def get_service() -> FashnVTONService:
    global _service
    if _service is None:
        # NEW: Use your utility to auto-detect the 4090 and set the correct dtype (bf16)
        device, dtype = configure_inference_mode()
        
        print(f"--- Initializing FashnVTONService on {device} with {dtype} ---")
        
        # Pass the detected device to your service
        _service = FashnVTONService(
            weights_dir="./app/weights", 
            device=str(device) # Ensures 'cuda' is passed
        )
    return _service

@router.post("/tryon", response_model=TryOnResponse)
async def tryon(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    category: str = Form(...)
):
    # 1. Validate category
    valid_categories = ("tops", "bottoms", "one-pieces")
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}"
        )
    
    # 2. Get Service (triggers GPU init if first time)
    service = get_service()
    
    # 3. Clear GPU Cache before heavy work (Prevents OOM on 4090)
    GPUMemoryManager.clear_cache()
    
    try:
        person = Image.open(BytesIO(await person_image.read())).convert("RGB")
        garment = Image.open(BytesIO(await garment_image.read())).convert("RGB")
        
        # 4. Run Inference
        output_path = service.run(person, garment, category)
        
        return TryOnResponse(output_image_path=output_path)
    
    finally:
        # 5. Clear Cache after work to keep the GPU fresh for the next request
        GPUMemoryManager.clear_cache()
        GPUMemoryManager.log_memory()