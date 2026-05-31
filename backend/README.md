# InkLandscapeGen Backend

FastAPI backend for InkLandscapeGen. It provides scene-structure parsing, asynchronous generation task scheduling, image file management, history records, QR code generation, and runtime health checks.

## Structure

```text
backend/
  app/main.py                         FastAPI application entry
  app/routers/generation_router.py    REST API routes
  app/services/image_generator.py     Local image generation wrapper
  app/services/scene_graph_service.py Text parsing and scene-structure expansion
  app/qrcode.py                       QR code helper
  requirements.txt                    Python dependencies
```

## Main APIs

- `GET /api/v1/health`: backend, parser, device, GPU memory, and queue status.
- `POST /api/v1/scene-graph`: parse text into editable scene structure.
- `POST /api/v1/tasks`: create an asynchronous generation task.
- `GET /api/v1/tasks`: list recent generation tasks.
- `GET /api/v1/tasks/{task_id}`: query task status and result.
- `GET /api/v1/history`: list generated image history.
- `DELETE /api/v1/history/{filename}`: delete a generated image and history item.
- `GET /images/{filename}`: serve generated image files.
- `POST /api/v1/generate`: synchronous generation endpoint kept for compatibility.

## Install

```bash
cd /path/to/InkLandscapeGen/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

If you use a local editable copy of `diffusers`, add it to `PYTHONPATH` before starting the service.

## Configuration

Common environment variables:

```bash
export IMAGE_MODEL_DIR=/path/to/local/image-model
export GENERATED_IMAGE_DIR=/root/static/generated
export MAX_GENERATION_QUEUE=8
export MAX_TASK_RECORDS=80
export MAX_HISTORY_RECORDS=120
export CORS_ORIGINS=http://127.0.0.1:1024,http://localhost:1024
```

Optional parser and translation keys:

```bash
export DEEPSEEK_API_KEY=your_key
export ZHIPUAI_API_KEY=your_key
export BAIDU_TRANSLATE_APP_ID=your_app_id
export BAIDU_TRANSLATE_API_KEY=your_key
```

The repository intentionally does not include `.env`. Keep API keys outside version control.

## Run

GPU inference:

```bash
cd /path/to/InkLandscapeGen/backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use CPU offload when GPU memory is limited:

```bash
IMAGE_CPU_OFFLOAD=1 uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Use mock generation for frontend/backend integration without loading a local image model:

```bash
MOCK_GENERATION=1 uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Quick Check

```bash
curl -s http://127.0.0.1:8000/api/v1/health
```

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"远山云起，溪水绕亭。","style":"水墨","width":768,"height":512,"steps":12,"return_base64":false}'
```

## Scene Structure

The backend first tries to use the configured text semantic parser. If the external parser is unavailable, it falls back to deterministic rules:

```text
input text
  -> extract explicit imagery
  -> complete implicit landscape elements
  -> build entities, attributes, relations, and layout hints
  -> convert the structure into an image-generation prompt
```

This rule-based fallback is designed for robust demos and integration testing. A stronger trained scene-graph expansion module can be connected later through `scene_graph_service.py`.
