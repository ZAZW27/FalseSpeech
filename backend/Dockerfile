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

# Pre-download the Wav2Vec2-Small AntiDeepfake model from Hugging Face
# This bakes the model into the Docker image for faster cold starts
RUN python -c "from huggingface_hub import hf_hub_download; \
hf_hub_download('nii-yamagishilab/wav2vec-small-anti-deepfake', 'model.safetensors'); \
hf_hub_download('nii-yamagishilab/wav2vec-small-anti-deepfake', 'config.json')"

# Expose the port your app will run on (adjust if needed, e.g., 8000 for FastAPI)
EXPOSE 7860

# Define the command to run your app
# Replace 'app.py' with the name of your main Python script
CMD ["python", "app.py"]