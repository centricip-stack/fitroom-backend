# =============================================================================
# [VTON - UNDER DEVELOPMENT] Virtual Try-On Route
# This entire module is commented out while the VTON feature is under development.
# To re-enable: uncomment everything below AND re-enable vton_router in app/main.py
# =============================================================================

# from fastapi import APIRouter, UploadFile, File, Form
# from PIL import Image
# from io import BytesIO
# from app.models.schemas import TryOnResponse
# from app.core.pipeline import FashnVTONService

# router = APIRouter()
# service = FashnVTONService(weights_dir="./app/weights")

# @router.post("/tryon", response_model=TryOnResponse)
# async def tryon(
#     person_image: UploadFile = File(...),
#     garment_image: UploadFile = File(...),
#     category: str = Form(...)
# ):
#     person = Image.open(BytesIO(await person_image.read())).convert("RGB")
#     garment = Image.open(BytesIO(await garment_image.read())).convert("RGB")
#     output_path = service.run(person, garment, category)
#     return TryOnResponse(output_image_path=output_path)