import asyncio
import io
import json
import logging
import os
import torch
import torchaudio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from huggingface_hub import PyTorchModelHubMixin
from fairseq.models.wav2vec import Wav2Vec2Model, Wav2Vec2Config

# --- Configuration ---
MODEL_ID = "nii-yamagishilab/wav2vec-small-anti-deepfake"
TARGET_SR = 16000
CHUNK_DURATION_S = 10
CHUNK_SAMPLES = TARGET_SR * CHUNK_DURATION_S
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Model Definitions (from the official model card) ---
class SSLModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        cfg = Wav2Vec2Config(
            encoder_layers=12,
            encoder_embed_dim=768,
            quantize_targets=True,
            latent_dim=256,
            final_dim=256,
        )
        self.model = Wav2Vec2Model(cfg)

    def extract_feat(self, input_data):
        if input_data.ndim == 3:
            input_data = input_data[:, :, 0]
        with torch.no_grad():
            features = self.model(input_data.to(DEVICE), mask=False, features_only=True)['x']
        return features

class DeepfakeDetector(torch.nn.Module, PyTorchModelHubMixin):
    def __init__(self):
        super().__init__()
        self.ssl_orig_output_dim = 768
        self.num_classes = 2
        self.m_ssl = SSLModel()
        self.adap_pool1d = torch.nn.AdaptiveAvgPool1d(output_size=1)
        self.proj_fc = torch.nn.Linear(
            in_features=self.ssl_orig_output_dim,
            out_features=self.num_classes,
        )

    def forward(self, wav):
        emb = self.m_ssl.extract_feat(wav)
        emb = emb.transpose(1, 2)
        pooled_emb = self.adap_pool1d(emb)
        pooled_emb = pooled_emb.squeeze(-1)
        logits = self.proj_fc(pooled_emb)
        return logits

# --- Audio Preprocessing ---
def preprocess_audio(audio_bytes: bytes) -> torch.Tensor:
    """Loads raw audio bytes, converts to mono, resamples, and normalizes."""
    try:
        wav, sr = torchaudio.load(io.BytesIO(audio_bytes))
        wav = wav.mean(dim=0)  # Convert to mono
        if sr != TARGET_SR:
            wav = torchaudio.functional.resample(wav, sr, new_freq=TARGET_SR)
        with torch.no_grad():
            wav = torch.nn.functional.layer_norm(wav, wav.shape)
        return wav.unsqueeze(0).to(DEVICE)  # Add batch dim
    except Exception as e:
        logger.error(f"Error preprocessing audio: {e}")
        return None

# --- FastAPI App and WebSocket Endpoint ---
app = FastAPI()

# Load the model once on startup
model = None

@app.on_event("startup")
def load_model():
    global model
    logger.info(f"Loading AntiDeepfake model: {MODEL_ID}")
    model = DeepfakeDetector.from_pretrained(MODEL_ID)
    model.to(DEVICE)
    model.eval()
    logger.info(f"Model loaded successfully on {DEVICE}.")

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection established.")
    audio_buffer = bytearray()
    try:
        while True:
            # Receive a chunk of audio bytes from the client
            data = await websocket.receive_bytes()
            audio_buffer.extend(data)
            logger.info(f"Received {len(data)} bytes. Buffer size: {len(audio_buffer)} bytes.")

            # Once we have enough for a 10-second chunk, process it
            # Note: This is a rough estimate. A real implementation would track duration by samples.
            # For simplicity, we assume the client sends raw PCM data or that we can estimate.
            # A more robust approach would involve the client sending metadata.
            # Here, we'll just process the buffer when it's large enough.
            # Let's assume for now we process every time we have enough bytes.
            # We need to know the audio format. For WAV, it's bytes.
            # This part is tricky. Let's simplify: we'll just process the buffer as it comes in.
            # A better approach: client sends chunks of a known duration.
            
            # For this example, let's just try to process the buffer if it's large enough.
            # This is not perfect, but it's a starting point.
            if len(audio_buffer) > CHUNK_SAMPLES * 2:  # Rough estimate for 16-bit PCM
                # We have enough data, let's process it.
                # In a real app, you'd extract exactly CHUNK_SAMPLES worth.
                chunk_to_process = bytes(audio_buffer)
                audio_buffer = bytearray()  # Reset buffer

                wav_tensor = preprocess_audio(chunk_to_process)
                if wav_tensor is not None:
                    with torch.no_grad():
                        logits = model(wav_tensor)
                        probs = torch.nn.functional.softmax(logits, dim=1)
                        real_prob = probs[0][1].item()
                        fake_prob = probs[0][0].item()
                        is_fake = fake_prob > 0.5  # Simple threshold

                        result = {
                            "real_prob": real_prob,
                            "fake_prob": fake_prob,
                            "is_fake": is_fake,
                        }
                        await websocket.send_text(json.dumps(result))
                        logger.info(f"Sent result: {result}")

    except WebSocketDisconnect:
        logger.info("WebSocket connection disconnected.")
    except Exception as e:
        logger.error(f"An error occurred in the WebSocket handler: {e}")
        await websocket.close(code=1011)  # Internal error