from fastapi import FastAPI
# [VTON - UNDER DEVELOPMENT] from app.api.routes import router as vton_router
from app.api.skin_routes import router as skin_router
from app.api.admin_routes import router as admin_router

from fastapi.middleware.cors import CORSMiddleware







app = FastAPI(
    title="Fashn-VTON API",
    description=(
        "Virtual Try-On and Skin Analysis API.\n\n"
        # "[VTON - UNDER DEVELOPMENT] - **/tryon** — Try a garment on a person image.\n"
        "- **/skin-analysis** — Detect skin tone and recommend dresses from J., Bonanza, and Sapphire (DB).\n"
        "- **/admin/sync-sapphire** — Sync Sapphire collection to MongoDB Atlas."
    ),
    version="1.5.0",
)



app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # or ["*"] for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# [VTON - UNDER DEVELOPMENT] app.include_router(vton_router)
app.include_router(skin_router)
app.include_router(admin_router)
