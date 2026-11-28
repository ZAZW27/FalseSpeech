# Use a slim Python base image to keep the size down
FROM python:3.10-slim

# Install system-level dependencies needed for audio processing and building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN useradd -m -u 1000 appuser
WORKDIR /home/appuser/app

# Copy the requirements file first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
# 1. Upgrade pip
# 2. Install CPU-only PyTorch and Torchaudio
# 3. Install fairseq and its build dependencies (the repository recommends a specific commit)
# 4. Install the rest of the required packages
RUN pip install --no-cache-dir "pip==24.0" && \
    pip install --no-cache-dir torch torchaudio --extra-index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir Cython "numpy>=1.24,<2.0" && \
    pip install --no-cache-dir fairseq==0.12.2 --no-deps && \
    pip install --no-cache-dir hydra-core==1.0.7 omegaconf==2.0.6 regex sacrebleu tqdm cffi bitarray portalocker && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Change ownership to the appuser
RUN chown -R appuser:appuser /home/appuser/app
USER appuser

# Pre-download the Wav2Vec2-Large AntiDeepfake model and Silero VAD so cold starts never block
RUN python -c "from huggingface_hub import hf_hub_download; \
hf_hub_download('nii-yamagishilab/wav2vec-large-anti-deepfake', 'model.safetensors'); \
hf_hub_download('nii-yamagishilab/wav2vec-large-anti-deepfake', 'config.json')" && \
    python -c "import torch; torch.hub.load('snakers4/silero-vad', 'silero_vad', trust_repo=True)"

# Expose the port your app will run on (adjust if needed, e.g., 8000 for FastAPI)
EXPOSE 7860

# Run FastAPI via uvicorn in production mode
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]