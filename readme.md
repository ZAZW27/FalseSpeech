# False Speech

A hybrid web and Android system for real-time detection of AI-generated
and manipulated speech. The backend runs a zero-shot audio deepfake
classifier over a WebSocket connection and returns a True/False verdict
with a confidence score.

## Status

Academic project, in development. Backend inference engine and API
skeleton are functional. Frontend, authentication, payments, and the
Android client are pending.

## Repository Layout

    FalseSpeech/
      backend/      FastAPI server, inference engine, tests
      docs/         API contract, OpenAPI spec
      compose.yaml  Docker Compose orchestration
      README.md

The frontend (Vue 3 + Tailwind) will live in `frontend/` and is not yet
present.

## Stack

Backend:

- Python 3.10
- FastAPI and Uvicorn
- PyTorch (CPU)
- fairseq
- PostgreSQL 16
- SQLAlchemy 2.x
- Docker Compose

Frontend (planned):

- Vue 3
- Vite
- Tailwind CSS

## Model

This project uses the AntiDeepfake model released by Yamagishi Lab at
the National Institute of Informatics (NII), Japan.

- Model: `nii-yamagishilab/wav2vec-small-anti-deepfake`
- Repository: https://github.com/nii-yamagishilab/AntiDeepfake
- Paper: Post-training for Deepfake Speech Detection, ASRU 2025,
  https://arxiv.org/abs/2506.21090

The model is loaded at runtime from Hugging Face. It is not
redistributed in this repository. All credit for the detection model
belongs to the original authors. See Attribution below.

## Quick Start

Requires Docker and Docker Compose.

    git clone <this-repo-url>
    cd FalseSpeech
    docker compose up --build

The API will be available at:

- http://localhost:7860/ Health check
- http://localhost:7860/docs Swagger UI

PostgreSQL runs on port 5432.

## API

See [docs/API_CONTRACT.md](docs/API_CONTRACT.md) for the human-readable
contract and [docs/openapi.yaml](docs/openapi.yaml) for the machine-
readable OpenAPI 3.0 spec.

## Testing

    docker compose exec antideepfake-server python tests/test_ws.py backend/samples/fake/sample.wav

Sample audio files are not committed. Place your own `.wav` files under
`backend/samples/fake/` and `backend/samples/real/` to run the tests.

## Attribution

The audio deepfake detection model used by this project is developed by
Wanying Ge, Xin Wang, Xuechen Liu, and Junichi Yamagishi at Yamagishi
Lab, National Institute of Informatics, Japan.

All model weights are the intellectual property of NII. They are made
available for research and educational purposes under the Creative
Commons Attribution-NonCommercial-ShareAlike 4.0 International
(CC BY-NC-SA 4.0) license.

Citation:

    @inproceedings{antideepfake_2025,
        title={Post-training for Deepfake Speech Detection},
        author={Ge, Wanying and Wang, Xin and Liu, Xuechen and Yamagishi, Junichi},
        booktitle={2025 IEEE Automatic Speech Recognition and Understanding Workshop (ASRU)},
        year={2025}
    }

Project application code (this repository) is provided for academic
purposes as part of a university course assignment.
