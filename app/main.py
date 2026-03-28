from fastapi import FastAPI
# [VTON - UNDER DEVELOPMENT] from app.api.routes import router as vton_router
from app.api.skin_routes import router as skin_router
from app.api.admin_routes import router as admin_router
# ihave add this on 4/3/2026 1 line
from app.api.routes import router as vton_router
from fastapi.middleware.cors import CORSMiddleware

from app.services.gpu_memory_manager import GPUMemoryManager

from fastapi.staticfiles import StaticFiles
import os


app = FastAPI(
    title="Fashn-VTON API",
    description=(
        "Virtual Try-On and Skin Analysis API.\n\n"
        # "[VTON - UNDER DEVELOPMENT] - **/tryon** — Try a garment on a person image.\n"
        # i have add this on 4/3/2026
        "- **/tryon** - Try a garment on a person image.\n"
        "- **/skin-analysis** — Detect skin tone and recommend dresses from J., Bonanza, and Sapphire (DB).\n"
        "- **/admin/sync-sapphire** — Sync Sapphire collection to MongoDB Atlas."
    ),
    version="1.5.0",
)


@app.on_event("startup")
async def startup_event():
    # This prepares the RTX 4090 for high-performance inference
    GPUMemoryManager.setup_memory_efficient_mode()
    gpu_info = GPUMemoryManager.check_gpu_capability()
    print(f"--- RUNPOD GPU INITIALIZED ---")
    print(f"GPU Status: {gpu_info}")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# [VTON - UNDER DEVELOPMENT] app.include_router(vton_router)

# I have add this on 4/3/2026
app.include_router(vton_router)
app.include_router(skin_router)
app.include_router(admin_router)



