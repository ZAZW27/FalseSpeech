import os
from dotenv import load_dotenv

load_dotenv()

id_model = os.getenv("MODEL_ID", "nii-yamagishilab/wav2vec-small-anti-deepfake")
target_sr = int(os.getenv("TARGET_SR", "16000"))
chunk_dur = int(os.getenv("CHUNK_DURATION_S", "10"))
device = os.getenv("DEVICE", "auto")  # "cpu" | "cuda" | "auto"