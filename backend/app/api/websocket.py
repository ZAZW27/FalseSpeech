import json 
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import target_sr
from app.service import inference
from app.service.audio import preprocess_audio

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket): 
    await websocket.accept()
    logger.info("Websocket connected!!!")

    _, device = inference.get_model()
    
    try: 
        while True: 
            data = await websocket.receive_bytes()
            logger.info(f"Received {len(data):,} bytes")
            
            if not inference.is_loaded(): 
                await websocket.send_tet(json.dump({"error": "model belum siap"}))
                continue
            
            wav_tensor = preprocess_audio(data, target_sr=target_sr, device=device)
            if wav_tensor is None: 
                await websocket.send_text(json.dumps({"error": "audio gagal di decode"}))
                continue
            
            ril_prob, fek_prob = inference.inferencing(wav_tensor)
            result = {
                "real_prob": ril_prob, 
                "fake_prob": fek_prob, 
                "is_fake": fek_prob > 0.5
            }
            await websocket.send_text(json.dumps(result))
            logger.info(f"Sent: {result}")
            
    except WebSocketDisconnect: 
        logger.info("WebSocket disconnected")
    except Exception as e: 
        logger.error(f"WS ERROR: {e}", exc_info=True)
        try: 
            await websocket.close(code=1011)
        except Exception: 
            pass