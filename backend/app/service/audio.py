import io
import logging
import subprocess

import soundfile as sf
import torch
import torchaudio

logger = logging.getLogger(__name__)


def _is_webm(data: bytes) -> bool:
    return len(data) >= 4 and data[:4] == b"\x1a\x45\xdf\xa3"

def _webm_to_wav(data: bytes) -> bytes | None:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-f", "wav",
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg decode failed: {result.stderr.decode()[:200]}")
            return None
        return result.stdout
    except Exception as e:
        logger.error(f"ffmpeg transcode error: {e}")
        return None


def preprocess_audio(audio_bytes: bytes, target_sr: int, device):
    try:
        if _is_webm(audio_bytes):
            wav_bytes = _webm_to_wav(audio_bytes)
            if wav_bytes is None:
                return None
            audio_bytes = wav_bytes

        wav_np, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
        wav_np = wav_np.mean(axis=1)
        wav = torch.from_numpy(wav_np)

        if sr != target_sr:
            wav = torchaudio.functional.resample(wav, sr, new_freq=target_sr)

        with torch.no_grad():
            wav = torch.nn.functional.layer_norm(wav, wav.shape)

        return wav.unsqueeze(0).to(device)
    except Exception as e:
        logger.error(f"preprocess_audio failed: {e}")
        return None