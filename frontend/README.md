# InkLandscapeGen Frontend

Vue3 frontend for InkLandscapeGen. It provides a modern Chinese landscape painting workspace with poem input, generation controls, editable scene structure, asynchronous task progress, history management, image comparison, runtime status, icons, and Chinese/English UI switching.

## Structure

```text
frontend/
  src/main.js          Vue entry
  src/App.vue          Main workspace
  public/              Static assets
  vue.config.js        Dev server and proxy config
  package.json         Scripts and dependencies
```

## Features

- Poem or natural-language prompt input.
- Style selection: default, ink wash, blue-green, and light-crimson landscape styles.
- Composition, width, height, steps, seed, detail level, blank-space level, and negative prompt controls.
- Editable scene structure with explicit imagery, expanded imagery, attributes, relations, layout, and style hints.
- Asynchronous task submission through `/api/v1/tasks`.
- Progress display for parsing, generation, and result saving.
- Generated image preview, history records, parameter reuse, deletion, and multi-image comparison.
- Runtime status page for backend connection, parser mode, inference device, GPU memory, and queue capacity.
- Icon-based navigation and actions using `@lucide/vue`.
- Chinese/English UI switching with preference stored in browser `localStorage`.

## Install

```bash
cd /path/to/InkLandscapeGen/frontend
npm install
```

## Development

```bash
cd /path/to/InkLandscapeGen/frontend
npm run serve
```

The dev server uses port `1024` by default. API requests to `/api` and image requests to `/images` are proxied to `http://127.0.0.1:8000`.

Open:

```text
http://127.0.0.1:1024/
```

## Production Build

```bash
cd /path/to/InkLandscapeGen/frontend
npm run build
python -m http.server 1024 --bind 127.0.0.1 --directory dist
```

If the backend is not running at `http://127.0.0.1:8000`, set `VUE_APP_API_BASE` before building:

```bash
VUE_APP_API_BASE=http://your-backend-host:8000 npm run build
```

## Notes

- Default generation parameters are `768x512`, `28` steps, and seed `20260529`.
- For quick UI testing, start the backend with `MOCK_GENERATION=1`.
- The production build may show bundle-size warnings because Element Plus and static images are included; these warnings do not prevent deployment.
