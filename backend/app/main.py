import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import id_model, device
from app.service import inference, scheduler
from app.api.routes import router as http_router
from app.api.websocket import router as ws_router
from app.db.init_db import init_db
from app.limiter import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI): 
    init_db()
    inference.loading_model(id_model, device)
    inference.start_priority_worker()
    scheduler.start_subscription_scheduler()
    yield
    await inference.stop_priority_worker()
    await scheduler.stop_subscription_scheduler()
    logger.info("shutting down.")
    
app = FastAPI(title="False Speech", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
_cors_origins = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]
_frontend_url = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _frontend_url and _frontend_url not in _cors_origins:
    _cors_origins.append(_frontend_url)
_cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", r"https?://.*").strip() or None

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(http_router)
app.include_router(ws_router)