import base64
import io
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from ..services.image_generator import GENERATED_DIR, STYLE_PROMPTS, image_generator
from ..services.scene_graph_service import analyze_scene_graph, scene_graph_parser_status, scene_graph_to_prompt


router = APIRouter()
TASK_EXECUTOR = ThreadPoolExecutor(max_workers=1)
TASKS: dict[str, dict[str, Any]] = {}
TASK_LOCK = threading.Lock()
HISTORY_FILE = GENERATED_DIR / "history.json"
MAX_QUEUE_SIZE = int(os.getenv("MAX_GENERATION_QUEUE", "8"))
MAX_TASK_RECORDS = int(os.getenv("MAX_TASK_RECORDS", "80"))
MAX_HISTORY_RECORDS = int(os.getenv("MAX_HISTORY_RECORDS", "120"))


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)
    style: str = "默认"
    width: int = Field(default=768, ge=256, le=1280)
    height: int = Field(default=512, ge=256, le=1280)
    steps: int = Field(default=12, ge=1, le=80)
    guidance_scale: float = Field(default=4.0, ge=0.0, le=10.0)
    seed: int | None = None
    negative_prompt: str = Field(default="文字、水印、现代建筑、摄影质感、卡通风格", max_length=300)
    composition: str = "自动"
    detail_level: int = Field(default=70, ge=0, le=100)
    blank_level: int = Field(default=45, ge=0, le=100)
    scene_graph_override: dict[str, Any] | None = None
    return_base64: bool = True


class LegacyGenerateRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=500)
    style: str = "默认"


class GeneratedImage(BaseModel):
    filename: str
    url: str
    base64: str | None = None
    qrcode: str | None = None


class GenerateResponse(BaseModel):
    status: Literal["succeeded"]
    images: list[GeneratedImage]
    prompt: str
    style: str
    elapsed_ms: int
    seed: int
    width: int
    height: int
    scene_graph: dict[str, Any]


class SceneGraphRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=500)


def _payload_dict(payload: BaseModel) -> dict[str, Any]:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()


def _make_qrcode_base64(url: str) -> str:
    try:
        from ..qrcode import generate_qr_code_new

        qr_code = generate_qr_code_new(url)
    except Exception:
        qr_code = Image.new("RGB", (144, 144), "white")
        draw = ImageDraw.Draw(qr_code)
        draw.rectangle((8, 8, 136, 136), outline="black", width=2)
        draw.text((28, 60), "IMAGE", fill="black")
    buffered = io.BytesIO()
    qr_code.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")


def _public_image_url(request: Request, filename: str) -> str:
    return str(request.url_for("get_generated_image", filename=filename))


def _public_image_url_from_base(base_url: str, filename: str) -> str:
    return f"{base_url.rstrip('/')}/images/{filename}"


def _classify_error(exc: Exception) -> str:
    message = str(exc)
    lower = message.lower()
    if "out of memory" in lower or "cuda" in lower and "memory" in lower:
        return "显存不足：请降低尺寸或推理步数，或开启低显存模式后重试。"
    if "connection" in lower or "timeout" in lower:
        return "外部文本解析服务暂时不可用，系统已尽量回退；请稍后重试。"
    return message or "生成失败，请检查后端服务。"


def _safe_generated_path(filename: str) -> Path:
    if Path(filename).name != filename:
        raise HTTPException(status_code=403, detail="非法文件路径")

    generated_root = GENERATED_DIR.resolve()
    safe_path = (generated_root / filename).resolve()
    try:
        safe_path.relative_to(generated_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="非法文件路径") from exc
    return safe_path


def _active_task_count_locked() -> int:
    return sum(1 for item in TASKS.values() if item.get("status") in {"queued", "running"})


def _prune_tasks_locked() -> None:
    if len(TASKS) <= MAX_TASK_RECORDS:
        return

    items = sorted(TASKS.items(), key=lambda item: item[1].get("created_at", ""), reverse=True)
    keep_ids = {task_id for task_id, _task in items[:MAX_TASK_RECORDS]}
    keep_ids.update(
        task_id
        for task_id, task in items
        if task.get("status") in {"queued", "running"}
    )
    for task_id in list(TASKS):
        if task_id not in keep_ids:
            del TASKS[task_id]


def _history_records() -> list[dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_history(records: list[dict[str, Any]]) -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = HISTORY_FILE.with_suffix(".json.tmp")
    temp_file.write_text(
        json.dumps(records[:MAX_HISTORY_RECORDS], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp_file.replace(HISTORY_FILE)


def _append_history(record: dict[str, Any]) -> None:
    with TASK_LOCK:
        records = _history_records()
        records = [item for item in records if item.get("filename") != record.get("filename")]
        records.insert(0, record)
        _write_history(records)


def _record_to_public(request: Request, record: dict[str, Any]) -> dict[str, Any]:
    filename = record.get("filename", "")
    item = dict(record)
    if filename:
        item["url"] = _public_image_url(request, filename)
    return item


def _scan_generated_files(request: Request) -> list[dict[str, Any]]:
    records = []
    for path in sorted(GENERATED_DIR.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        records.append(
            {
                "id": path.stem,
                "filename": path.name,
                "url": _public_image_url(request, path.name),
                "created_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                "prompt": "历史生成图像",
                "style": "未知",
                "width": None,
                "height": None,
                "elapsed_ms": None,
                "seed": None,
                "scene_graph": {},
                "params": {},
            }
        )
    return records


def _create_generation_record(
    payload: dict[str, Any],
    result,
    scene_graph: dict[str, Any],
    task_id: str | None = None,
) -> dict[str, Any]:
    return {
        "id": task_id or uuid.uuid4().hex,
        "filename": result.filename,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "prompt": payload["prompt"],
        "style": payload["style"],
        "width": result.width,
        "height": result.height,
        "elapsed_ms": result.elapsed_ms,
        "seed": result.seed,
        "scene_graph": scene_graph,
        "params": {
            "composition": payload.get("composition"),
            "steps": payload.get("steps"),
            "guidance_scale": payload.get("guidance_scale"),
            "detail_level": payload.get("detail_level"),
            "blank_level": payload.get("blank_level"),
            "negative_prompt": payload.get("negative_prompt"),
        },
        "generated_prompt": result.prompt,
    }


def _generate_from_payload(payload: dict[str, Any], task_id: str | None = None):
    scene_graph = payload.get("scene_graph_override") or analyze_scene_graph(payload["prompt"])
    generation_text = scene_graph_to_prompt(payload["prompt"], scene_graph)
    result = image_generator.generate(
        generation_text,
        payload["style"],
        payload["width"],
        payload["height"],
        payload["steps"],
        payload["guidance_scale"],
        payload.get("seed"),
        payload.get("negative_prompt", ""),
        payload.get("composition", "自动"),
        payload.get("detail_level", 70),
        payload.get("blank_level", 45),
    )
    record = _create_generation_record(payload, result, scene_graph, task_id)
    _append_history(record)
    return result, scene_graph, record


def _task_public_state(task: dict[str, Any], request: Request) -> dict[str, Any]:
    item = dict(task)
    result = item.get("result")
    if isinstance(result, dict) and result.get("filename"):
        result = dict(result)
        result["url"] = _public_image_url(request, result["filename"])
        item["result"] = result
    return item


def _run_generation_task(task_id: str, payload: dict[str, Any], base_url: str) -> None:
    with TASK_LOCK:
        TASKS[task_id].update({"status": "running", "stage": "解析场景图", "progress": 18})
    try:
        scene_graph = payload.get("scene_graph_override") or analyze_scene_graph(payload["prompt"])
        with TASK_LOCK:
            TASKS[task_id].update({"stage": "图像生成", "progress": 48, "scene_graph": scene_graph})

        generation_text = scene_graph_to_prompt(payload["prompt"], scene_graph)
        result = image_generator.generate(
            generation_text,
            payload["style"],
            payload["width"],
            payload["height"],
            payload["steps"],
            payload["guidance_scale"],
            payload.get("seed"),
            payload.get("negative_prompt", ""),
            payload.get("composition", "自动"),
            payload.get("detail_level", 70),
            payload.get("blank_level", 45),
        )
        record = _create_generation_record(payload, result, scene_graph, task_id)
        _append_history(record)
        image_url = _public_image_url_from_base(base_url, result.filename)
        with TASK_LOCK:
            TASKS[task_id].update(
                {
                    "status": "succeeded",
                    "stage": "结果保存",
                    "progress": 100,
                    "result": {
                        "filename": result.filename,
                        "url": image_url,
                        "qrcode": _make_qrcode_base64(image_url),
                        "elapsed_ms": result.elapsed_ms,
                        "seed": result.seed,
                        "width": result.width,
                        "height": result.height,
                    },
                    "history": record,
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            _prune_tasks_locked()
    except Exception as exc:
        with TASK_LOCK:
            TASKS[task_id].update(
                {
                    "status": "failed",
                    "stage": "异常处理",
                    "progress": 100,
                    "error": _classify_error(exc),
                    "finished_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            _prune_tasks_locked()


def _to_response(
    request: Request,
    payload: dict[str, Any],
    result,
    return_base64: bool,
    scene_graph: dict[str, Any],
) -> GenerateResponse:
    image_url = _public_image_url(request, result.filename)
    image_base64 = image_generator.image_to_base64(result.filename) if return_base64 else None
    return GenerateResponse(
        status="succeeded",
        images=[
            GeneratedImage(
                filename=result.filename,
                url=image_url,
                base64=image_base64,
                qrcode=_make_qrcode_base64(image_url),
            )
        ],
        prompt=result.prompt,
        style=payload["style"],
        elapsed_ms=result.elapsed_ms,
        seed=result.seed,
        width=result.width,
        height=result.height,
        scene_graph=scene_graph,
    )


@router.get("/api/v1/health")
async def api_health():
    with TASK_LOCK:
        active_tasks = _active_task_count_locked()
        running_tasks = sum(1 for item in TASKS.values() if item.get("status") == "running")
        queued_tasks = sum(1 for item in TASKS.values() if item.get("status") == "queued")
        total_tasks = len(TASKS)
    return {
        "status": "ok",
        "styles": list(STYLE_PROMPTS.keys()),
        "generator": image_generator.status(),
        "scene_graph_parser": scene_graph_parser_status(),
        "task_queue": {
            "total": total_tasks,
            "running": running_tasks,
            "queued": queued_tasks,
            "active": active_tasks,
            "max_queue_size": MAX_QUEUE_SIZE,
            "available_slots": max(MAX_QUEUE_SIZE - active_tasks, 0),
            "max_task_records": MAX_TASK_RECORDS,
        },
    }


@router.get("/health")
async def health():
    return await api_health()


@router.post("/api/v1/scene-graph")
async def api_scene_graph(payload: SceneGraphRequest):
    return await run_in_threadpool(analyze_scene_graph, payload.prompt)


@router.post("/api/v1/generate", response_model=GenerateResponse)
async def api_generate(request: Request, payload: GenerateRequest):
    data = _payload_dict(payload)
    try:
        result, scene_graph, _record = await run_in_threadpool(_generate_from_payload, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=_classify_error(exc)) from exc
    return _to_response(request, data, result, payload.return_base64, scene_graph)


@router.post("/api/v1/tasks")
async def create_generation_task(request: Request, payload: GenerateRequest):
    task_id = uuid.uuid4().hex
    data = _payload_dict(payload)
    task = {
        "id": task_id,
        "status": "queued",
        "stage": "等待调度",
        "progress": 5,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "prompt": data["prompt"],
        "style": data["style"],
        "params": {
            "composition": data.get("composition"),
            "width": data.get("width"),
            "height": data.get("height"),
            "steps": data.get("steps"),
            "seed": data.get("seed"),
            "detail_level": data.get("detail_level"),
            "blank_level": data.get("blank_level"),
        },
    }
    with TASK_LOCK:
        _prune_tasks_locked()
        active_tasks = _active_task_count_locked()
        if active_tasks >= MAX_QUEUE_SIZE:
            raise HTTPException(
                status_code=429,
                detail=f"生成队列已满：当前排队或运行任务 {active_tasks} 个，上限 {MAX_QUEUE_SIZE} 个。请稍后再试。",
            )
        TASKS[task_id] = task
    base_url = str(request.base_url).rstrip("/")
    TASK_EXECUTOR.submit(_run_generation_task, task_id, data, base_url)
    return task


@router.get("/api/v1/tasks")
async def list_generation_tasks(request: Request):
    with TASK_LOCK:
        _prune_tasks_locked()
        items = [_task_public_state(task, request) for task in TASKS.values()]
    items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return {"items": items[:50]}


@router.get("/api/v1/tasks/{task_id}")
async def get_generation_task(task_id: str, request: Request):
    with TASK_LOCK:
        task = TASKS.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return _task_public_state(task, request)


@router.get("/api/v1/history")
async def list_history(request: Request):
    records = [_record_to_public(request, item) for item in _history_records()]
    if not records:
        records = _scan_generated_files(request)
    return {"items": records}


@router.delete("/api/v1/history/{filename}")
async def delete_history_item(filename: str):
    safe_path = _safe_generated_path(filename)
    with TASK_LOCK:
        records = [item for item in _history_records() if item.get("filename") != filename]
        _write_history(records)
    if safe_path.exists() and safe_path.is_file():
        safe_path.unlink()
    return {"status": "deleted", "filename": filename}


@router.post("/generate-image-new/", response_model=GenerateResponse)
@router.post("/generate-image-new2/", response_model=GenerateResponse)
async def legacy_generate(request: Request, payload: LegacyGenerateRequest):
    data = {
        "prompt": payload.description,
        "style": payload.style,
        "width": 768,
        "height": 512,
        "steps": 12,
        "guidance_scale": 4.0,
        "seed": None,
        "negative_prompt": "文字、水印、现代建筑、摄影质感、卡通风格",
        "composition": "自动",
        "detail_level": 70,
        "blank_level": 45,
        "return_base64": True,
        "scene_graph_override": None,
    }
    try:
        result, scene_graph, _record = await run_in_threadpool(_generate_from_payload, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=_classify_error(exc)) from exc
    return _to_response(request, data, result, True, scene_graph)


@router.get("/images/{filename}", name="get_generated_image")
@router.get("/api/images/{filename}", name="get_generated_image_api")
async def get_generated_image(filename: str):
    safe_path = _safe_generated_path(filename)
    if not safe_path.exists() or not safe_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")

    return FileResponse(safe_path)
