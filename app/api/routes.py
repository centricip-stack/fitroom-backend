from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image
from io import BytesIO
from typing import Literal
import os
from app.models.schemas import TryOnResponse
from app.core.pipeline import FashnVTONService

router = APIRouter()
_service = None

def get_service() -> FashnVTONService:
    global _service
    if _service is None:
        # Read device from environment variable (default: cuda if available, else cpu)
        device = os.getenv("TRYON_DEVICE", None)  # None = auto-detect
        _service = FashnVTONService(weights_dir="./app/weights", device=device)
    return _service

@router.post("/tryon", response_model=TryOnResponse)
async def tryon(
    person_image: UploadFile = File(...),
    garment_image: UploadFile = File(...),
    category: str = Form(...)
):
    # Validate category
    valid_categories = ("tops", "bottoms", "one-pieces")
    if category not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category '{category}'. Must be one of: {', '.join(valid_categories)}"
        )
    
    service = get_service()
    person = Image.open(BytesIO(await person_image.read())).convert("RGB")
    garment = Image.open(BytesIO(await garment_image.read())).convert("RGB")
    output_path = service.run(person, garment, category)
    return TryOnResponse(output_image_path=output_path)




