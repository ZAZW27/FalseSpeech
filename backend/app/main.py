import logging 
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import id_model, device
from app.service import inference
from app.api.routes import router as http_router
from app.api.websocket import router as ws_router

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI): 
    inference.loading_model(id_model, device)
    yield
    logger.info("shutting down.")
    
app = FastAPI(title="False Speech", lifespan=lifespan)

app.include_router(http_router)
app.include_router(ws_router)