import logging
import torch

from app.models.detector import detectorDeepfake

logger = logging.getLogger(__name__)

_model = None
_device = None

def loading_model(model_id: str, device_pref: str = "auto"): 
    global _model, _device
    
    if device_pref == "auto": 
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else: 
        _device = torch.device(device_pref)
    
    logger.info(f"Loading AntiDeepfake model: {model_id} on {_device}")
    _model = detectorDeepfake(device=str(_device)).from_pretrained(model_id)
    _model.to(_device)
    _model.eval()
    logger.info(f"Model loaded on {_device}")
    return _model, _device

def get_model(): 
    return _model, _device

def is_loaded() -> bool:
    return _model is not None

def inferencing(wav_tensor): 
    if _model is None: 
        raise RuntimeError("Model ga ada woi")
    
    with torch.no_grad(): 
        logits = _model(wav_tensor)
        kemungkinan = torch.nn.functional.softmax(logits, dim=1)
        ril_prob = float(kemungkinan[0][1].item())
        fek_prob = float(kemungkinan[0][0].item())
    return ril_prob, fek_prob