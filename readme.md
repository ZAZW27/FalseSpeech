# False Speech

A hybrid web and Android system for real-time detection of AI-generated and manipulated speech. The backend runs a zero-shot audio deepfake classifier over a WebSocket connection and returns a True/False verdict with a confidence score.

## Project Status: ~65% Complete

This project is an academic assignment and is currently in active development. The core engine, backend, and functional UI are fully operational.

| Component           | Progress | Status                                                                               |
| :------------------ | :------- | :----------------------------------------------------------------------------------- |
| **AI Engine**       | 85%      | Wav2Vec2-Large running zero-shot. (Fine-tuning for modern TTS is a future task).     |
| **Web Backend**     | 85%      | FastAPI, JWT Auth, WebSockets, Quota system, History API.                            |
| **Database**        | 100%     | PostgreSQL with SQLAlchemy, fully migrated and integrated.                           |
| **Web Frontend**    | 70%      | Functional plain HTML/JS UI (Login, Live Detection, History). Vue 3 rewrite pending. |
| **Payment Gateway** | 0%       | Midtrans integration is stubbed for future release.                                  |
| **Android App**     | 0%       | Planned for future release.                                                          |
| **Deployment/TLS**  | 10%      | Dockerized locally. Nginx/TLS setup pending.                                         |

## Repository Layout

```text
FalseSpeech/
  backend/      FastAPI server, inference engine, tests, static UI
  docs/         API contract, OpenAPI spec
  compose.yaml  Docker Compose orchestration
  README.md
```

## Stack

**Backend:** Python 3.10, FastAPI, Uvicorn, PyTorch (CPU), fairseq, PostgreSQL 16, SQLAlchemy 2.x, Docker Compose.

**Frontend:** Vanilla HTML/JS (Live Test UI). Vue 3 + Tailwind planned.

## Model

This project uses the AntiDeepfake model released by Yamagishi Lab at the National Institute of Informatics (NII), Japan.

- Model: `nii-yamagishilab/wav2vec-large-anti-deepfake`
- Repository: https://github.com/nii-yamagishilab/AntiDeepfake
- Paper: Post-training for Deepfake Speech Detection, ASRU 2025, https://arxiv.org/abs/2506.21090

The model is loaded at runtime from Hugging Face. It is not redistributed in this repository. All credit for the detection model belongs to the original authors. See Attribution below.

## Quick Start (Easy Deployment)

Requires Docker and Docker Compose installed.

1. Clone the repository and enter the directory:

```bash
git clone https://github.com/ZAZW27/FalseSpeech.git
cd FalseSpeech
```

2. Start the application (this will download the AI model and build the database):

```bash
docker compose up --build
```

3. Wait for the server to load the model (approx. 1-2 minutes). Look for:
   `INFO | app.service.inference | Model loaded on cpu`

4. Access the application:

- **Web Interface:** http://localhost:7860/static/login.html
- **Swagger API Docs:** http://localhost:7860/docs
- **Health Check:** http://localhost:7860/

## Database Management (Backup & Restore)

To share the database or move it to a new server, use these commands.

**Export Database (Backup):**
Run this on your local machine to create a `.sql` file:

```bash
docker compose exec -T db pg_dump -U falsespeech falsespeech > falsespeech_backup.sql
```

**Import Database (Restore):**
If someone else clones the repo and wants your exact data, they can run:

```bash
cat falsespeech_backup.sql | docker compose exec -T db psql -U falsespeech -d falsespeech
```

## API & Testing

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the human-readable contract and [docs/openapi.yaml](docs/openapi.yaml) for the machine-readable OpenAPI 3.0 spec.

To test the WebSocket inference via CLI:

```bash
docker compose exec antideepfake-server python tests/test_ws.py samples/Fake-sample/test.wav <YOUR_JWT_TOKEN>
```

## Attribution

The audio deepfake detection model used by this project is developed by Wanying Ge, Xin Wang, Xuechen Liu, and Junichi Yamagishi at Yamagishi Lab, National Institute of Informatics, Japan.

All model weights are the intellectual property of NII. They are made available for research and educational purposes under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0) license.

Citation:

```bibtex
@inproceedings{antideepfake_2025,
    title={Post-training for Deepfake Speech Detection},
    author={Ge, Wanying and Wang, Xin and Liu, Xuechen and Yamagishi, Junichi},
    booktitle={2025 IEEE Automatic Speech Recognition and Understanding Workshop (ASRU)},
    year={2025}
}
```

Project application code (this repository) is provided for academic purposes as part of a university course assignment.
