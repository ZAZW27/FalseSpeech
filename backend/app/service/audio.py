import io 
import logging
import soundfile as sf
import torch
import torchaudio

logger = logging.getLogger(__name__)

def preprocess_audio(audio_bytes: bytes, target_sr: int, device): 
    try: 
        wav_np, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32", always_2d=True)
        wav_np = wav_np.mean(axis=1) 
        wav = torch.from_numpy(wav_np)
        
        if sr != target_sr: 
            wav = torchaudio.functional.resample(wav, sr, new_freq=target_sr)
            
        with torch.no_grad(): 
            wav = torch.nn.functional.layer_norm(wav, wav.shape)
            
        return wav.unsqueeze(0).to(device)
    except Exception as e: 
        logger.error(f"preprocess audio gagal :( > {e})")
        return None