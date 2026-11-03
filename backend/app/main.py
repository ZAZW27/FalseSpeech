import logging 
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import id_model, device
from app.service import inference
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
    yield
    logger.info("shutting down.")
    
app = FastAPI(title="False Speech", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(http_router)
app.include_router(ws_router)