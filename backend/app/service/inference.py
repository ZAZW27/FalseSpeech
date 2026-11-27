import asyncio
import itertools
import logging
from typing import Optional, Tuple
import torch

logger = logging.getLogger(__name__)

_model = None
_feature_extractor = None
_device = None
_backend_kind = "hf"  # "hf" (transformers AutoModelForAudioClassification) | "legacy" (nii-yamagishilab)
_real_idx = 0
_fake_idx = 1

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


def _resolve_label_indices(id2label: dict) -> Tuple[int, int]:
    """Determines (real_idx, fake_idx) dynamically from HuggingFace model config.id2label."""
    real_idx, fake_idx = None, None
    for raw_k, raw_v in (id2label or {}).items():
        idx = int(raw_k)
        label = str(raw_v).strip().lower()
        if any(tok in label for tok in ("fake", "spoof", "ai", "synth", "deepfake", "generated")):
            fake_idx = idx
        elif any(tok in label for tok in ("real", "bona", "human", "genuine", "authentic")):
            real_idx = idx
    if real_idx is not None and fake_idx is not None:
        return real_idx, fake_idx
    if fake_idx is not None:
        return (1 - fake_idx), fake_idx
    if real_idx is not None:
        return real_idx, (1 - real_idx)
    # Fallback default for standard HF binary audio classification (0=Real, 1=Fake)
    return 0, 1


def loading_model(model_id: str, device_pref: str = "auto"):
    global _model, _feature_extractor, _device, _backend_kind, _real_idx, _fake_idx

    if device_pref == "auto":
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        _device = torch.device(device_pref)

    logger.info(f"Loading AntiDeepfake model: {model_id} on {_device}")

    if model_id.startswith("nii-yamagishilab/"):
        from app.models.detector import detectorDeepfake

        _backend_kind = "legacy"
        _feature_extractor = None
        _model = detectorDeepfake(device=str(_device)).from_pretrained(model_id)
        _model.to(_device)
        _model.eval()
        _real_idx, _fake_idx = 1, 0
    else:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

        _backend_kind = "hf"
        _feature_extractor = AutoFeatureExtractor.from_pretrained(model_id)
        _model = AutoModelForAudioClassification.from_pretrained(model_id)
        _model.to(_device)
        _model.eval()
        _real_idx, _fake_idx = _resolve_label_indices(getattr(_model.config, "id2label", {}))
        logger.info(
            f"HF id2label={getattr(_model.config, 'id2label', {})} -> "
            f"real_idx={_real_idx}, fake_idx={_fake_idx}"
        )

    logger.info(f"Model loaded ({_backend_kind}) on {_device}")
    return _model, _device


def get_model():
    return _model, _device


def is_loaded() -> bool:
    return _model is not None


def inferencing(wav_tensor) -> Tuple[float, float]:
    if _model is None:
        raise RuntimeError("Model ga ada woi")

    with torch.no_grad():
        if _backend_kind == "legacy":
            logits = _model(wav_tensor)
        else:
            audio_np = wav_tensor.squeeze(0).detach().cpu().numpy()
            inputs = _feature_extractor(
                audio_np,
                sampling_rate=16000,
                return_tensors="pt",
                padding=True,
            )
            inputs = {k: v.to(_device) for k, v in inputs.items()}
            logits = _model(**inputs).logits

        probs = torch.nn.functional.softmax(logits, dim=-1)
        ril_prob = float(probs[0][_real_idx].item())
        fek_prob = float(probs[0][_fake_idx].item())
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
