import asyncio
import itertools
import logging
from typing import Optional, Tuple
import torch

from app.models.detector import detectorDeepfake

logger = logging.getLogger(__name__)

_model = None
_device = None

# RF-10.1: Tier-based AI Inference Priority Queue
# Lower integer = higher priority: Pro Max & Lifetime (0) > Pro (1) > Free (2)
TIER_PRIORITY = {
    "lifetime": 0,
    "pro_max": 0,
    "pro": 1,
    "free": 2,
}

_queue: Optional[asyncio.PriorityQueue] = None
_worker_task: Optional[asyncio.Task] = None
_seq = itertools.count()


def get_tier_priority(tier: str) -> int:
    return TIER_PRIORITY.get((tier or "free").lower(), 2)


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


def inferencing(wav_tensor) -> Tuple[float, float]:
    if _model is None:
        raise RuntimeError("Model ga ada woi")

    with torch.no_grad():
        logits = _model(wav_tensor)
        kemungkinan = torch.nn.functional.softmax(logits, dim=1)
        ril_prob = float(kemungkinan[0][1].item())
        fek_prob = float(kemungkinan[0][0].item())
    return ril_prob, fek_prob


async def _priority_worker() -> None:
    assert _queue is not None
    logger.info("AI Priority Queue worker started (Pro Max/Lifetime > Pro > Free)")
    while True:
        priority, _seq_id, wav_tensor, future = await _queue.get()
        try:
            if not future.cancelled():
                result = await asyncio.to_thread(inferencing, wav_tensor)
                if not future.cancelled():
                    future.set_result(result)
        except Exception as exc:
            if not future.cancelled():
                future.set_exception(exc)
        finally:
            _queue.task_done()


def start_priority_worker() -> None:
    global _queue, _worker_task
    if _queue is None:
        _queue = asyncio.PriorityQueue()
    if _worker_task is None or _worker_task.done():
        _worker_task = asyncio.create_task(_priority_worker())


async def stop_priority_worker() -> None:
    global _worker_task
    if _worker_task and not _worker_task.done():
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
    _worker_task = None


async def enqueue_inference(wav_tensor, tier: str = "free") -> Tuple[float, float]:
    """Enqueues an audio tensor into the tier-prioritized AI inference queue."""
    start_priority_worker()
    assert _queue is not None

    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()
    priority = get_tier_priority(tier)
    await _queue.put((priority, next(_seq), wav_tensor, future))
    return await future
