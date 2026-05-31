# /app/main.py
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from .routers.generation_router import router as generation_router

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.append(str(backend_dir))

app = FastAPI(title="Chinese Landscape Painting Generation API")

static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

# 添加 CORS 中间件，演示环境默认开放；部署时可通过 CORS_ORIGINS 限定前端域名。
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=os.getenv("CORS_ALLOW_CREDENTIALS", "0") == "1",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generation_router)

