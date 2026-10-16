import io
import logging
import subprocess

import soundfile as sf
import torch
import torchaudio

logger = logging.getLogger(__name__)

def preprocess_audio(audio_bytes: bytes, target_sr: int, device):
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error",
                "-i", "pipe:0",
                "-ac", "1",                    # mono
                "-ar", str(target_sr),         # resample to 16kHz
                "-f", "wav",
                "pipe:1",
            ],
            input=audio_bytes,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg failed: {result.stderr.decode()[:200]}")
            return None

        wav_np, sr = sf.read(
            io.BytesIO(result.stdout),
            dtype="float32",
            always_2d=False,
        )
        wav = torch.from_numpy(wav_np)

        with torch.no_grad():
            wav = torch.nn.functional.layer_norm(wav, wav.shape)

        return wav.unsqueeze(0).to(device)
    except Exception as e:
        logger.error(f"preprocess_audio failed: {e}")
        return None