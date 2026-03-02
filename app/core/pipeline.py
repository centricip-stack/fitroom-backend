# =============================================================================
# [VTON - UNDER DEVELOPMENT] FashnVTONService Pipeline
# This module is commented out while the VTON feature is under development.
# To re-enable: uncomment everything below AND re-enable vton_router in app/main.py
# =============================================================================

# from fashn_vton import TryOnPipeline
# from PIL import Image
# import os

# class FashnVTONService:
#     def __init__(self, weights_dir: str = "./weights"):
#         self.pipeline = TryOnPipeline(weights_dir=weights_dir)
#
#     def run(self, person_image: Image.Image, garment_image: Image.Image, category: str, save_dir="./outputs"):
#         os.makedirs(save_dir, exist_ok=True)
#         result = self.pipeline(person_image=person_image, garment_image=garment_image, category=category)
#         output_path = os.path.join(save_dir, "output.png")
#         result.images[0].save(output_path)
#         return output_path