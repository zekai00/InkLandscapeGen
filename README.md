# 中国山水画智能生成系统

最后更新时间：2026-05-31 12:54:38 CST

InkLandscapeGen 是一个面向中国山水画辅助创作的前后端项目，提供诗词输入、语义解析、场景结构编辑、异步生成任务、历史记录、多图对比、二维码分享和系统状态监控等功能。

当前系统已作为独立仓库上传至 GitHub：

```text
https://github.com/zekai00/InkLandscapeGen
```

## Directory

```text
system/
  .gitignore         Git 上传忽略规则
  backend/          FastAPI 后端服务
  frontend/         Vue3 前端工作台
  reports/          系统整理、联调和更新报告
  .env              本地环境变量
```

## Features

- 诗词或自然语言描述输入。
- 文本语义解析与规则回退。
- 可编辑场景结构，包括显式意象、补全意象、属性、关系、布局和风格提示。
- 异步生成任务队列，支持队列容量控制和任务状态轮询。
- 生成历史记录、参数复用、删除和多图对比。
- 系统状态页，显示后端服务、文本解析状态、推理设备、显存和队列信息。
- 前端支持图标化操作按钮和中英双语切换。

## Backend

```bash
cd /root/Workspace/ControllableImageGeneration/system/backend
PYTHONPATH=/root/Workspace/diffusers/src uvicorn app.main:app --host 127.0.0.1 --port 8000
```

常用环境变量：

```bash
export GENERATED_IMAGE_DIR=/root/static/generated
export MAX_GENERATION_QUEUE=8
export MAX_TASK_RECORDS=80
export MAX_HISTORY_RECORDS=120
export CORS_ORIGINS=http://127.0.0.1:1024,http://localhost:1024
```

只联调界面时可启用模拟生成：

```bash
MOCK_GENERATION=1 PYTHONPATH=/root/Workspace/diffusers/src uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：

```bash
curl -s http://127.0.0.1:8000/api/v1/health
```

## Frontend

```bash
cd /root/Workspace/ControllableImageGeneration/system/frontend
npm install
npm run serve
```

生产构建：

```bash
cd /root/Workspace/ControllableImageGeneration/system/frontend
npm run build
python -m http.server 1024 --bind 127.0.0.1 --directory dist
```

访问地址：

```text
http://127.0.0.1:1024/
```

如果后端不在 `127.0.0.1:8000`，构建前设置：

```bash
VUE_APP_API_BASE=http://你的后端地址:8000 npm run build
```

## GitHub

当前本地仓库位于：

```bash
cd /root/Workspace/ControllableImageGeneration/system
git status
git remote -v
```

当前目录已提供 `.gitignore`，默认忽略 `.env`、前端构建产物、依赖目录和临时文件。后续提交前仍建议检查 `git status --short`，不要把真实 API Key 上传到公开仓库。
