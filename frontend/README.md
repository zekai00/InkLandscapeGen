# 前端运行说明

当前前端入口为 `src/main.js`，主页面为 `src/App.vue`。旧版 `App-*.vue` 文件已移到 `src/legacy/`，避免继续干扰当前联调入口。

## 安装依赖

```bash
cd /root/Workspace/ControllableImageGeneration/system/frontend
npm install
```

## 开发模式

```bash
cd /root/Workspace/ControllableImageGeneration/system/frontend
npm run serve
```

开发服务器默认端口为 `1024`，并将 `/api`、`/images` 代理到 `http://127.0.0.1:8000`。如果当前系统文件监听数不足，开发模式可能报 `ENOSPC`，此时建议使用下面的生产构建方式联调。

## 生产构建联调

```bash
cd /root/Workspace/ControllableImageGeneration/system/frontend
npm run build
python -m http.server 1024 --bind 127.0.0.1 --directory dist
```

然后访问：

```bash
http://127.0.0.1:1024/
```

`src/App.vue` 默认请求 `http://127.0.0.1:8000`。如果后端部署在其他地址，构建前设置：

```bash
VUE_APP_API_BASE=http://你的后端地址:8000 npm run build
```

## 当前页面功能

- 输入诗词或自然语言描述。
- 选择默认、水墨、青绿、浅绛四类山水画风格。
- 调整构图模式、尺寸、推理步数、随机种子、细节强度、留白强度和负面约束。
- 调用 `/api/v1/tasks` 创建异步生成任务，并轮询任务阶段和进度。
- 展示生成图、推理耗时、种子、尺寸和可编辑场景结构。
- 支持生成历史记录、参数复用、删除、多图对比和系统状态监控。
- 使用 `@lucide/vue` 为导航和关键操作增加图标。
- 支持中英双语切换，语言设置保存在浏览器本地存储中。

前端默认参数为 768x512、28 step，适合正常展示；需要快速预览时可手动降低尺寸和步数。
