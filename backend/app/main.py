import logging 
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import id_model, device
from app.service import inference
from app.api.routes import router as http_router
from app.api.websocket import router as ws_router
from app.db.init_db import init_db


logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI): 
    init_db()
    inference.loading_model(id_model, device)
    yield
    logger.info("shutting down.")
    
app = FastAPI(title="False Speech", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(http_router)
app.include_router(ws_router)