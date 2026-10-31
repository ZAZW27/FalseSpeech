import os
from dotenv import load_dotenv

load_dotenv()
jwt_secret = os.getenv("JWT_SECRET", "dev-only-change-me-in-prod")
jwt_algo = "HS256"
jwt_expires = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

id_model = os.getenv("MODEL_ID", "nii-yamagishilab/wav2vec-small-anti-deepfake")
target_sr = int(os.getenv("TARGET_SR", "16000"))
chunk_dur = int(os.getenv("CHUNK_DURATION_S", "10"))
device = os.getenv("DEVICE", "auto")  # "cpu" | "cuda" | "auto"

