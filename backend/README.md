# 后端运行说明

当前后端入口为 `app/main.py`，主路由为 `app/routers/generation_router.py`，生成服务为 `app/services/image_generator.py`。

## 当前接口

- `GET /api/v1/health`：检查后端、设备和生成器状态。
- `POST /api/v1/scene-graph`：调用文本语义解析服务生成结构化场景图，失败时回退规则补全。
- `POST /api/v1/generate`：当前前端使用的主生成接口。
- `POST /generate-image-new/`、`POST /generate-image-new2/`：保留给旧前端的兼容接口。
- `GET /images/{filename}`：读取生成后的图片。

## 生成服务配置

默认使用本地图像生成服务，不加载 LoRA。若需要修改本地权重目录，可以设置：

```bash
export IMAGE_MODEL_DIR=/path/to/local/image-model
```

工程控制相关环境变量如下：

```bash
export GENERATED_IMAGE_DIR=/root/static/generated
export MAX_GENERATION_QUEUE=8
export MAX_TASK_RECORDS=80
export MAX_HISTORY_RECORDS=120
export CORS_ORIGINS=http://127.0.0.1:8080,http://localhost:8080
```

其中，`MAX_GENERATION_QUEUE` 用于限制等待或运行中的生成任务数量，避免用户连续提交导致显存资源被长期占用；`MAX_TASK_RECORDS` 用于限制内存中的任务状态记录数量；历史记录写入采用临时文件替换方式，降低服务中断时 `history.json` 损坏的风险。

本环境里的 Python 需要使用本地推理库源码：

```bash
cd /root/Workspace/ControllableImageGeneration/system/backend
PYTHONPATH=/root/Workspace/diffusers/src uvicorn app.main:app --host 127.0.0.1 --port 8000
```

默认有 CUDA 时直接使用 GPU 推理。若显存不足，可回退到 CPU offload：

```bash
cd /root/Workspace/ControllableImageGeneration/system/backend
IMAGE_CPU_OFFLOAD=1 PYTHONPATH=/root/Workspace/diffusers/src uvicorn app.main:app --host 127.0.0.1 --port 8000
```

如果只想调通前后端界面，不想等待真实模型推理，可以启用模拟模式：

```bash
cd /root/Workspace/ControllableImageGeneration/system/backend
MOCK_GENERATION=1 PYTHONPATH=/root/Workspace/diffusers/src uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 最小测试

```bash
curl -s http://127.0.0.1:8000/api/v1/health
```

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"远山云起，溪水绕亭。","style":"水墨","width":768,"height":512,"steps":12,"return_base64":false}'
```

首次推理会先加载本地生成服务，耗时明显较长。

## 场景图说明

当前系统的“诗词解析”和“场景图扩充”优先调用文本语义解析服务输出 JSON，服务不可用时回退到确定性规则流程：

```text
输入诗词
  -> 关键词抽取显式意象
  -> 根据山水画常识补全隐含意象
  -> 生成实体、属性、关系和布局提示
  -> 将场景图摘要写入图像生成提示
```

该流程适合系统演示和前后端联调；若要和论文算法完全一致，需要继续接入完整训练式场景图扩充模块。

## 二维码说明

生成接口会返回图片 URL 和二维码 base64。二维码依赖 `qrcode[pil]`，依赖已写入 `requirements.txt`：

```bash
pip install -r requirements.txt
```

## 文件整理

旧版 SD 1.5、LoRA 和旧图片路由代码已归档到 `app/legacy_sd15/`，当前启动流程不会引用这些文件。
