<template>
  <div class="app-shell">
    <div class="paper-texture"></div>
    <div class="ink-field" aria-hidden="true">
      <span
        v-for="index in 30"
        :key="index"
        class="ink-stroke"
        :style="particleStyle(index)"
      ></span>
    </div>

    <aside class="side-nav">
      <div class="brand-mark">
        <div class="seal">山</div>
        <div>
          <h1>{{ t('appTitle') }}</h1>
          <p>{{ t('appSubtitle') }}</p>
        </div>
      </div>

      <nav class="nav-list">
        <button
          v-for="item in views"
          :key="item.key"
          class="nav-item"
          :class="{ active: activeView === item.key }"
          @click="activeView = item.key"
        >
          <span class="nav-icon"><component :is="item.icon" :size="17" /></span>
          <span>{{ t(item.labelKey) }}</span>
        </button>
      </nav>

      <div class="queue-tile">
        <div class="queue-title">{{ t('queueTitle') }}</div>
        <div class="queue-numbers">
          <span><b>{{ queueInfo.running }}</b>{{ t('running') }}</span>
          <span><b>{{ queueInfo.queued }}</b>{{ t('queued') }}</span>
        </div>
        <div class="status-dot" :class="{ online: health.status === 'ok' }">
          {{ health.status === 'ok' ? t('serviceOk') : t('connecting') }}
        </div>
      </div>
    </aside>

    <main class="workspace">
      <header class="topbar">
        <div>
          <p class="eyebrow">{{ t('eyebrow') }}</p>
          <h2>{{ currentViewTitle }}</h2>
        </div>
        <div class="top-actions">
          <el-button class="icon-button" round @click="toggleLanguage">
            <Languages :size="16" />
            <span>{{ lang === 'zh' ? 'EN' : '中文' }}</span>
          </el-button>
          <el-button class="icon-button" round @click="refreshAll">
            <RefreshCw :size="16" />
            <span>{{ t('refreshStatus') }}</span>
          </el-button>
          <el-button class="icon-button" round type="primary" @click="startGeneration" :loading="submitting">
            <Play :size="16" />
            <span>{{ t('startGeneration') }}</span>
          </el-button>
        </div>
      </header>

      <section v-if="activeView === 'studio'" class="studio-layout">
        <section class="panel input-panel">
          <div class="panel-heading">
            <div>
              <p class="section-kicker">{{ t('creationInput') }}</p>
              <h3>{{ t('poemAndControl') }}</h3>
            </div>
            <el-tag round effect="plain">{{ parserLabel }}</el-tag>
          </div>

          <el-input
            v-model="form.prompt"
            class="poem-input"
            type="textarea"
            :rows="6"
            maxlength="500"
            show-word-limit
            :placeholder="t('promptPlaceholder')"
          />

          <div class="quick-prompts">
            <button v-for="item in samplePrompts" :key="item" @click="useSamplePrompt(item)">
              {{ item }}
            </button>
          </div>

          <div class="control-grid">
            <label class="control-block">
              <span>{{ t('styleLabel') }}</span>
              <el-radio-group v-model="form.style">
                <el-radio-button v-for="item in styleOptions" :key="item" :label="item">
                  {{ optionLabel('style', item) }}
                </el-radio-button>
              </el-radio-group>
            </label>

            <label class="control-block">
              <span>{{ t('compositionLabel') }}</span>
              <el-select v-model="form.composition" :placeholder="t('compositionPlaceholder')">
                <el-option
                  v-for="item in compositionOptions"
                  :key="item"
                  :label="optionLabel('composition', item)"
                  :value="item"
                />
              </el-select>
            </label>

            <label class="control-block">
              <span>{{ t('width') }}</span>
              <el-input-number v-model="form.width" :min="256" :max="1280" :step="32" controls-position="right" />
            </label>

            <label class="control-block">
              <span>{{ t('height') }}</span>
              <el-input-number v-model="form.height" :min="256" :max="1280" :step="32" controls-position="right" />
            </label>

            <label class="control-block">
              <span>{{ t('steps') }}</span>
              <el-input-number v-model="form.steps" :min="1" :max="80" :step="1" controls-position="right" />
            </label>

            <label class="control-block">
              <span>{{ t('seed') }}</span>
              <el-input-number v-model="form.seed" :min="0" :max="2147483647" controls-position="right" />
            </label>
          </div>

          <div class="slider-row">
            <div>
              <div class="slider-title">
                <span>{{ t('detailLevel') }}</span>
                <b>{{ form.detail_level }}</b>
              </div>
              <el-slider v-model="form.detail_level" :min="0" :max="100" />
            </div>
            <div>
              <div class="slider-title">
                <span>{{ t('blankLevel') }}</span>
                <b>{{ form.blank_level }}</b>
              </div>
              <el-slider v-model="form.blank_level" :min="0" :max="100" />
            </div>
          </div>

          <label class="control-block full">
            <span>{{ t('negativePrompt') }}</span>
            <el-input
              v-model="form.negative_prompt"
              :placeholder="t('negativePlaceholder')"
            />
          </label>

          <div class="main-actions">
            <el-button class="icon-button" @click="analyzeSceneGraph" :loading="analyzing">
              <Search :size="16" />
              <span>{{ t('analyzeChain') }}</span>
            </el-button>
            <el-button class="icon-button" type="primary" @click="startGeneration" :loading="submitting">
              <ListPlus :size="16" />
              <span>{{ t('enqueue') }}</span>
            </el-button>
          </div>
        </section>

        <section class="output-column">
          <section class="panel result-panel">
            <div class="panel-heading">
              <div>
                <p class="section-kicker">{{ t('generationResult') }}</p>
                <h3>{{ taskTitle }}</h3>
              </div>
              <el-tag v-if="task.status" round :type="taskTagType">{{ statusLabel(task.status) }}</el-tag>
            </div>

            <div v-if="task.id" class="task-progress">
              <div class="progress-meta">
                <span>{{ stageLabel(task.stage || '等待调度') }}</span>
                <b>{{ task.progress || 0 }}%</b>
              </div>
              <el-progress
                :percentage="task.progress || 0"
                :stroke-width="12"
                :show-text="false"
                :status="task.status === 'failed' ? 'exception' : undefined"
              />
              <div class="progress-steps">
                <span :class="{ done: (task.progress || 0) >= 18 }">{{ t('semanticParsing') }}</span>
                <span :class="{ done: (task.progress || 0) >= 48 }">{{ t('imageGeneration') }}</span>
                <span :class="{ done: (task.progress || 0) >= 100 }">{{ t('resultSaving') }}</span>
              </div>
            </div>

            <el-alert
              v-if="errorMessage"
              class="error-alert"
              :title="errorMessage"
              type="error"
              :closable="false"
              show-icon
            />

            <div v-if="currentImage" class="image-stage">
              <img :src="currentImage.url" :alt="t('generatedImageAlt')" />
              <div class="image-toolbar">
                <span>{{ currentImage.width || form.width }} × {{ currentImage.height || form.height }}</span>
                <span v-if="currentImage.seed !== null && currentImage.seed !== undefined">Seed {{ currentImage.seed }}</span>
                <el-button class="icon-button" size="small" round @click="openImage(currentImage.url)">
                  <ExternalLink :size="14" />
                  <span>{{ t('openOriginal') }}</span>
                </el-button>
              </div>
            </div>

            <div v-else class="showcase">
              <div v-if="recentImages.length" class="showcase-grid">
                <button
                  v-for="item in recentImages.slice(0, 6)"
                  :key="item.filename"
                  class="showcase-item"
                  @click="previewHistory(item)"
                >
                  <img :src="item.url" :alt="item.prompt || t('historyImage')" />
                  <span>{{ optionLabel('style', item.style || '默认') }}</span>
                </button>
              </div>
              <div v-else class="empty-showcase">
                <div class="mountain-line"></div>
                <p>{{ t('emptyShowcase') }}</p>
              </div>
            </div>
          </section>

          <section class="panel link-panel">
            <div class="panel-heading">
              <div>
                <p class="section-kicker">{{ t('thesisChain') }}</p>
                <h3>{{ t('editableSceneStructure') }}</h3>
              </div>
              <el-button class="icon-button" size="small" round @click="resetGraphDraft">
                <RotateCcw :size="14" />
                <span>{{ t('restoreParsed') }}</span>
              </el-button>
            </div>

            <div class="chapter-flow">
              <article>
                <span>{{ t('chapter3') }}</span>
                <strong>{{ t('dataLayer') }}</strong>
                <p>{{ t('dataLayerDesc') }}</p>
              </article>
              <article>
                <span>{{ t('chapter4') }}</span>
                <strong>{{ t('semanticExpansion') }}</strong>
                <p>{{ t('semanticExpansionDesc') }}</p>
              </article>
              <article>
                <span>{{ t('chapter5') }}</span>
                <strong>{{ t('generationControl') }}</strong>
                <p>{{ t('generationControlDesc') }}</p>
              </article>
            </div>

            <div class="graph-editor">
              <label>
                <span>{{ t('explicitImagery') }}</span>
                <el-input v-model="graphDraft.entities" :placeholder="t('explicitPlaceholder')" />
              </label>
              <label>
                <span>{{ t('expandedImagery') }}</span>
                <el-input v-model="graphDraft.expanded_entities" :placeholder="t('expandedPlaceholder')" />
              </label>
              <label>
                <span>{{ t('visualAttributes') }}</span>
                <el-input v-model="graphDraft.attributes" :placeholder="t('attributesPlaceholder')" />
              </label>
              <label>
                <span>{{ t('spatialRelations') }}</span>
                <el-input
                  v-model="graphDraft.relations"
                  type="textarea"
                  :rows="2"
                  :placeholder="t('relationsPlaceholder')"
                />
              </label>
              <label>
                <span>{{ t('layoutPlan') }}</span>
                <el-input
                  v-model="graphDraft.layout"
                  type="textarea"
                  :rows="2"
                  :placeholder="t('layoutPlaceholder')"
                />
              </label>
              <label>
                <span>{{ t('styleHints') }}</span>
                <el-input v-model="graphDraft.style_hints" :placeholder="t('styleHintsPlaceholder')" />
              </label>
            </div>
          </section>
        </section>
      </section>

      <section v-else-if="activeView === 'history'" class="page-panel">
        <div class="page-heading">
          <div>
            <p class="section-kicker">{{ t('imageManagement') }}</p>
            <h3>{{ t('historyTitle') }}</h3>
          </div>
          <el-button class="icon-button" round @click="loadHistory">
            <RefreshCw :size="16" />
            <span>{{ t('refreshHistory') }}</span>
          </el-button>
        </div>

        <div v-if="historyList.length" class="history-grid">
          <article v-for="item in historyList" :key="item.filename" class="history-card">
            <img :src="item.url" :alt="item.prompt || t('historyImage')" />
            <div class="history-body">
              <div class="history-title">{{ item.prompt || t('historyImage') }}</div>
              <div class="history-meta">
                <span>{{ optionLabel('style', item.style || '默认') }}</span>
                <span>{{ formatDate(item.created_at) }}</span>
              </div>
              <div class="history-actions">
                <el-button class="icon-button" size="small" round @click="reuseRecord(item)">
                  <CopyCheck :size="14" />
                  <span>{{ t('reuseParams') }}</span>
                </el-button>
                <el-button class="icon-button" size="small" round @click="toggleCompare(item)">
                  <PanelTop :size="14" />
                  <span>{{ isInCompare(item) ? t('removeCompare') : t('addCompare') }}</span>
                </el-button>
                <el-button class="icon-button" size="small" round type="danger" plain @click="deleteHistory(item)">
                  <Trash2 :size="14" />
                  <span>{{ t('delete') }}</span>
                </el-button>
              </div>
            </div>
          </article>
        </div>
        <el-empty v-else :description="t('noHistory')" />
      </section>

      <section v-else-if="activeView === 'compare'" class="page-panel">
        <div class="page-heading">
          <div>
            <p class="section-kicker">{{ t('compareKicker') }}</p>
            <h3>{{ t('compareTitle') }}</h3>
          </div>
          <el-button class="icon-button" round @click="compareList = []">
            <Eraser :size="16" />
            <span>{{ t('clearCompare') }}</span>
          </el-button>
        </div>

        <div v-if="compareList.length" class="compare-grid">
          <article v-for="item in compareList" :key="item.filename" class="compare-card">
            <img :src="item.url" :alt="item.prompt || t('compareImage')" />
            <div>
              <h4>{{ optionLabel('style', item.style || '默认') }}</h4>
              <p>{{ item.prompt || t('historyImage') }}</p>
              <dl>
                <div><dt>{{ t('size') }}</dt><dd>{{ item.width || '-' }} × {{ item.height || '-' }}</dd></div>
                <div><dt>{{ t('stepsShort') }}</dt><dd>{{ item.params && item.params.steps ? item.params.steps : '-' }}</dd></div>
                <div><dt>Seed</dt><dd>{{ item.seed !== null && item.seed !== undefined ? item.seed : '-' }}</dd></div>
              </dl>
            </div>
          </article>
        </div>
        <div v-else class="compare-empty">
          <p>{{ t('compareEmpty') }}</p>
          <el-button class="icon-button" type="primary" round @click="activeView = 'history'">
            <ImagePlus :size="16" />
            <span>{{ t('chooseImages') }}</span>
          </el-button>
        </div>
      </section>

      <section v-else class="page-panel">
        <div class="page-heading">
          <div>
            <p class="section-kicker">{{ t('runtimeStatus') }}</p>
            <h3>{{ t('serviceQueueMemory') }}</h3>
          </div>
          <el-button class="icon-button" round @click="checkHealth">
            <RefreshCw :size="16" />
            <span>{{ t('refreshStatus') }}</span>
          </el-button>
        </div>

        <div class="status-grid">
          <article class="status-card">
            <span>{{ t('backendService') }}</span>
            <strong>{{ health.status === 'ok' ? t('normal') : t('offline') }}</strong>
            <p>{{ t('backendDesc') }}</p>
          </article>
          <article class="status-card">
            <span>{{ t('textParsing') }}</span>
            <strong>{{ parserLabel }}</strong>
            <p>{{ parserHint }}</p>
          </article>
          <article class="status-card">
            <span>{{ t('inferenceDevice') }}</span>
            <strong>{{ deviceLabel }}</strong>
            <p>{{ memoryHint }}</p>
          </article>
          <article class="status-card">
            <span>{{ t('taskQueue') }}</span>
            <strong>{{ queueInfo.running }} / {{ queueInfo.queued }}</strong>
            <p>{{ queueHint }}</p>
          </article>
        </div>

        <div class="queue-table">
          <div class="table-head">
            <span>{{ t('taskId') }}</span>
            <span>{{ t('status') }}</span>
            <span>{{ t('stage') }}</span>
            <span>{{ t('progress') }}</span>
          </div>
          <div v-if="taskRows.length">
            <div v-for="item in taskRows" :key="item.id" class="table-row">
              <span>{{ item.id.slice(0, 8) }}</span>
              <span>{{ statusLabel(item.status) }}</span>
              <span>{{ stageLabel(item.stage) }}</span>
              <span>{{ item.progress }}%</span>
            </div>
          </div>
          <div v-else class="table-empty">{{ t('noTasks') }}</div>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import axios from 'axios';
import {
  Activity,
  Columns3,
  CopyCheck,
  Eraser,
  ExternalLink,
  History,
  ImagePlus,
  Languages,
  LayoutDashboard,
  ListPlus,
  PanelTop,
  Palette,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Trash2,
} from '@lucide/vue';

const API_BASE = process.env.VUE_APP_API_BASE || 'http://127.0.0.1:8000';

const I18N = {
  zh: {
    appTitle: '山水画智能生成工作台',
    appSubtitle: '诗词语义解析 · 场景结构编辑 · 可控图像生成',
    navStudio: '创作台',
    navHistory: '历史记录',
    navCompare: '多图对比',
    navStatus: '系统状态',
    queueTitle: '生成队列',
    running: '运行',
    queued: '等待',
    serviceOk: '服务正常',
    connecting: '连接中',
    eyebrow: '面向中国山水画的可控生成系统',
    refreshStatus: '刷新状态',
    startGeneration: '启动生成',
    creationInput: '创作输入',
    poemAndControl: '诗词与生成控制',
    promptPlaceholder: '例如：明月松间照，清泉石上流。',
    styleLabel: '山水画风格',
    compositionLabel: '构图模式',
    compositionPlaceholder: '选择构图',
    width: '宽度',
    height: '高度',
    steps: '推理步数',
    seed: '随机种子',
    detailLevel: '细节强度',
    blankLevel: '留白强度',
    negativePrompt: '反向约束',
    negativePlaceholder: '例如：文字、水印、现代建筑、摄影质感',
    analyzeChain: '解析研究链路',
    enqueue: '加入生成队列',
    generationResult: '生成结果',
    semanticParsing: '语义解析',
    imageGeneration: '图像生成',
    resultSaving: '结果保存',
    generatedImageAlt: '生成的山水画结果',
    openOriginal: '打开原图',
    historyImage: '历史生成图像',
    emptyShowcase: '输入诗词并启动生成后，结果会保存在这里，也会进入历史记录和多图对比。',
    thesisChain: '论文链路',
    editableSceneStructure: '从数据到算法的可编辑场景结构',
    restoreParsed: '恢复解析结果',
    chapter3: '第三章',
    chapter4: '第四章',
    chapter5: '第五章',
    dataLayer: '数据层',
    semanticExpansion: '语义扩充',
    generationControl: '生成控制',
    dataLayerDesc: '从诗词中抽取显式意象、触发词与画面属性。',
    semanticExpansionDesc: '补全隐含意象，组织实体关系与布局线索。',
    generationControlDesc: '将场景结构转化为风格、构图与扩散生成约束。',
    explicitImagery: '显式意象',
    expandedImagery: '补全意象',
    visualAttributes: '画面属性',
    spatialRelations: '空间关系',
    layoutPlan: '布局安排',
    styleHints: '风格提示',
    explicitPlaceholder: '山体、水体、云雾',
    expandedPlaceholder: '远山、溪流、松林',
    attributesPlaceholder: '远近层次、虚实留白、传统笔墨',
    relationsPlaceholder: '云雾环绕远山；水体沿山石流动',
    layoutPlaceholder: '远山位于画面上方；溪流从中景延伸至前景',
    styleHintsPlaceholder: '水墨层次、青绿设色、淡雾',
    imageManagement: '图像管理',
    historyTitle: '生成历史记录',
    refreshHistory: '刷新历史',
    reuseParams: '复用参数',
    addCompare: '加入对比',
    removeCompare: '移出对比',
    delete: '删除',
    noHistory: '暂无历史图像',
    compareKicker: '多图对比',
    compareTitle: '不同参数与构图结果横向查看',
    clearCompare: '清空对比',
    compareImage: '对比图像',
    size: '尺寸',
    stepsShort: '步数',
    compareEmpty: '从“生成历史记录”中选择 2 到 4 张图像后，可在这里对比不同构图、风格与参数的效果。',
    chooseImages: '去选择图像',
    runtimeStatus: '运行状态',
    serviceQueueMemory: '服务、队列与显存提示',
    backendService: '后端服务',
    normal: '正常',
    offline: '未连接',
    backendDesc: '用于诗词解析、任务调度、图像生成和历史文件管理。',
    textParsing: '文本解析',
    inferenceDevice: '推理设备',
    taskQueue: '任务队列',
    taskId: '任务编号',
    status: '状态',
    stage: '阶段',
    progress: '进度',
    noTasks: '暂无任务记录',
    llmParser: '语义解析服务',
    ruleParser: '规则解析回退',
    llmParserHint: '系统优先使用文本语义解析服务抽取场景结构，失败时自动回退到规则解析。',
    ruleParserHint: '当前使用关键词规则和山水画常识补全，适合演示和低成本联调。',
    unknown: '未知',
    gpuInference: 'GPU 推理',
    noMemoryInfo: '未获取到显存信息；若生成失败，请降低尺寸或步数后重试。',
    memoryInfo: '可用显存 {free} MB / 总显存 {total} MB。显存不足时建议先降低尺寸、步数或细节强度。',
    queueInfo: '队列采用单任务顺序执行，当前占用 {active}/{max} 个槽位，超出上限时系统会拒绝新任务以保护显存。',
    queueFallback: '队列采用单任务顺序执行，避免多个生成任务同时抢占显存。',
    taskRunning: '生成任务进行中',
    taskSucceeded: '生成完成',
    taskFailed: '生成失败',
    recentPreview: '近期结果预览',
    inputRequired: '请输入诗词或画面描述。',
    parseFailed: '场景结构解析失败',
    submitFailed: '任务提交失败',
    taskFailedHint: '生成失败，请查看系统状态。',
    taskFetchFailed: '任务状态获取失败',
    deleteFailed: '删除失败',
  },
  en: {
    appTitle: 'Landscape Painting Studio',
    appSubtitle: 'Poem parsing · Scene structure editing · Controllable generation',
    navStudio: 'Studio',
    navHistory: 'History',
    navCompare: 'Compare',
    navStatus: 'Status',
    queueTitle: 'Generation Queue',
    running: 'running',
    queued: 'queued',
    serviceOk: 'Service online',
    connecting: 'Connecting',
    eyebrow: 'Controllable Chinese Landscape Painting Generation',
    refreshStatus: 'Refresh',
    startGeneration: 'Generate',
    creationInput: 'Input',
    poemAndControl: 'Poem and Controls',
    promptPlaceholder: 'Example: Moonlight among pines, clear spring over stones.',
    styleLabel: 'Painting Style',
    compositionLabel: 'Composition',
    compositionPlaceholder: 'Select composition',
    width: 'Width',
    height: 'Height',
    steps: 'Steps',
    seed: 'Seed',
    detailLevel: 'Detail',
    blankLevel: 'Blank Space',
    negativePrompt: 'Negative Prompt',
    negativePlaceholder: 'Example: text, watermark, modern buildings, photo-real texture',
    analyzeChain: 'Analyze Chain',
    enqueue: 'Add to Queue',
    generationResult: 'Result',
    semanticParsing: 'Parsing',
    imageGeneration: 'Generation',
    resultSaving: 'Saving',
    generatedImageAlt: 'Generated landscape painting',
    openOriginal: 'Open Image',
    historyImage: 'Generated image',
    emptyShowcase: 'Enter a poem and start generation. Results will appear here, then enter history and comparison.',
    thesisChain: 'Thesis Pipeline',
    editableSceneStructure: 'Editable Scene Structure from Data to Algorithm',
    restoreParsed: 'Restore Parsed',
    chapter3: 'Chapter 3',
    chapter4: 'Chapter 4',
    chapter5: 'Chapter 5',
    dataLayer: 'Data Layer',
    semanticExpansion: 'Semantic Expansion',
    generationControl: 'Generation Control',
    dataLayerDesc: 'Extract explicit imagery, trigger words, and visual attributes from the poem.',
    semanticExpansionDesc: 'Complete implicit imagery and organize entities, relations, and layout cues.',
    generationControlDesc: 'Convert scene structure into style, composition, and diffusion constraints.',
    explicitImagery: 'Explicit Imagery',
    expandedImagery: 'Expanded Imagery',
    visualAttributes: 'Visual Attributes',
    spatialRelations: 'Spatial Relations',
    layoutPlan: 'Layout Plan',
    styleHints: 'Style Hints',
    explicitPlaceholder: 'mountains, water, clouds',
    expandedPlaceholder: 'distant mountains, stream, pine forest',
    attributesPlaceholder: 'depth, blank space, traditional brushwork',
    relationsPlaceholder: 'clouds surround distant mountains; water flows along rocks',
    layoutPlaceholder: 'distant mountains in upper region; stream extends from middle ground to foreground',
    styleHintsPlaceholder: 'ink layers, blue-green colors, light mist',
    imageManagement: 'Image Management',
    historyTitle: 'Generation History',
    refreshHistory: 'Refresh History',
    reuseParams: 'Reuse',
    addCompare: 'Compare',
    removeCompare: 'Remove',
    delete: 'Delete',
    noHistory: 'No generated images',
    compareKicker: 'Comparison',
    compareTitle: 'Compare Parameters and Composition Results',
    clearCompare: 'Clear',
    compareImage: 'Comparison image',
    size: 'Size',
    stepsShort: 'Steps',
    compareEmpty: 'Choose 2 to 4 images from history to compare composition, style, and parameter effects.',
    chooseImages: 'Choose Images',
    runtimeStatus: 'Runtime',
    serviceQueueMemory: 'Service, Queue, and GPU Memory',
    backendService: 'Backend',
    normal: 'Online',
    offline: 'Offline',
    backendDesc: 'Handles poem parsing, task scheduling, image generation, and history file management.',
    textParsing: 'Text Parsing',
    inferenceDevice: 'Inference Device',
    taskQueue: 'Task Queue',
    taskId: 'Task ID',
    status: 'Status',
    stage: 'Stage',
    progress: 'Progress',
    noTasks: 'No task records',
    llmParser: 'Semantic Parser',
    ruleParser: 'Rule Fallback',
    llmParserHint: 'The system uses text semantic parsing first and falls back to rules when it fails.',
    ruleParserHint: 'Keyword rules and landscape-painting priors are used for demo and lightweight debugging.',
    unknown: 'Unknown',
    gpuInference: 'GPU Inference',
    noMemoryInfo: 'GPU memory is unavailable. If generation fails, reduce size or steps and retry.',
    memoryInfo: 'Free GPU memory {free} MB / total {total} MB. If memory is insufficient, reduce size, steps, or detail level.',
    queueInfo: 'The queue runs one task at a time. Current usage is {active}/{max}; new tasks are rejected at the limit to protect GPU memory.',
    queueFallback: 'The queue runs one task at a time to avoid competing GPU memory usage.',
    taskRunning: 'Generating',
    taskSucceeded: 'Completed',
    taskFailed: 'Failed',
    recentPreview: 'Recent Preview',
    inputRequired: 'Please enter a poem or image description.',
    parseFailed: 'Scene structure parsing failed',
    submitFailed: 'Task submission failed',
    taskFailedHint: 'Generation failed. Please check system status.',
    taskFetchFailed: 'Failed to fetch task status',
    deleteFailed: 'Delete failed',
  },
};

const OPTION_LABELS = {
  style: {
    默认: { zh: '默认', en: 'Default' },
    水墨: { zh: '水墨', en: 'Ink Wash' },
    青绿: { zh: '青绿', en: 'Blue-Green' },
    浅绛: { zh: '浅绛', en: 'Light Crimson' },
  },
  composition: {
    自动: { zh: '自动', en: 'Auto' },
    横幅: { zh: '横幅', en: 'Horizontal' },
    竖幅: { zh: '竖幅', en: 'Vertical' },
    方幅: { zh: '方幅', en: 'Square' },
    远景: { zh: '远景', en: 'Long Shot' },
    近景: { zh: '近景', en: 'Close View' },
  },
};

const STATUS_LABELS = {
  queued: { zh: '等待中', en: 'Queued' },
  running: { zh: '运行中', en: 'Running' },
  succeeded: { zh: '已完成', en: 'Completed' },
  failed: { zh: '失败', en: 'Failed' },
};

const STAGE_LABELS = {
  等待调度: { zh: '等待调度', en: 'Waiting' },
  解析场景图: { zh: '解析场景图', en: 'Parsing Scene Graph' },
  图像生成: { zh: '图像生成', en: 'Generating Image' },
  结果保存: { zh: '结果保存', en: 'Saving Result' },
  异常处理: { zh: '异常处理', en: 'Error Handling' },
};

export default {
  name: 'App',
  components: {
    Activity,
    Columns3,
    CopyCheck,
    Eraser,
    ExternalLink,
    History,
    ImagePlus,
    Languages,
    LayoutDashboard,
    ListPlus,
    PanelTop,
    Play,
    RefreshCw,
    RotateCcw,
    Search,
    Trash2,
  },
  data() {
    return {
      activeView: 'studio',
      lang: typeof window !== 'undefined' ? (window.localStorage.getItem('landscape-ui-lang') || 'zh') : 'zh',
      views: [
        { key: 'studio', labelKey: 'navStudio', icon: Palette },
        { key: 'history', labelKey: 'navHistory', icon: History },
        { key: 'compare', labelKey: 'navCompare', icon: Columns3 },
        { key: 'status', labelKey: 'navStatus', icon: Activity },
      ],
      samplePrompts: [
        '明月松间照，清泉石上流。',
        '远上寒山石径斜，白云生处有人家。',
        '孤舟蓑笠翁，独钓寒江雪。',
      ],
      styleOptions: ['默认', '水墨', '青绿', '浅绛'],
      compositionOptions: ['自动', '横幅', '竖幅', '方幅', '远景', '近景'],
      form: {
        prompt: '明月松间照，清泉石上流。',
        style: '水墨',
        composition: '自动',
        width: 768,
        height: 512,
        steps: 28,
        guidance_scale: 4.0,
        seed: 20260529,
        detail_level: 70,
        blank_level: 45,
        negative_prompt: '文字、水印、现代建筑、摄影质感、卡通风格',
      },
      sceneGraph: null,
      graphDraft: {
        entities: '',
        expanded_entities: '',
        attributes: '',
        relations: '',
        layout: '',
        style_hints: '',
        extracted_terms: '',
      },
      historyList: [],
      compareList: [],
      task: {},
      taskRows: [],
      result: null,
      health: {},
      queueInfo: { running: 0, queued: 0 },
      analyzing: false,
      submitting: false,
      errorMessage: '',
      pollTimer: null,
    };
  },
  computed: {
    currentViewTitle() {
      const view = this.views.find((item) => item.key === this.activeView);
      return view ? this.t(view.labelKey) : this.t('navStudio');
    },
    parserLabel() {
      const parser = this.health.scene_graph_parser || {};
      if (parser.llm_enabled && parser.api_key_configured) {
        return this.t('llmParser');
      }
      return this.t('ruleParser');
    },
    parserHint() {
      const parser = this.health.scene_graph_parser || {};
      if (parser.llm_enabled && parser.api_key_configured) {
        return this.t('llmParserHint');
      }
      return this.t('ruleParserHint');
    },
    deviceLabel() {
      const generator = this.health.generator || {};
      if (!generator.device) {
        return this.t('unknown');
      }
      return generator.device === 'cuda' ? this.t('gpuInference') : generator.device;
    },
    memoryHint() {
      const memory = this.health.generator && this.health.generator.gpu_memory;
      if (!memory) {
        return this.t('noMemoryInfo');
      }
      return this.t('memoryInfo', { free: memory.free_mb, total: memory.total_mb });
    },
    queueHint() {
      const queue = this.health.task_queue || {};
      const active = queue.active !== undefined ? queue.active : (this.queueInfo.running + this.queueInfo.queued);
      if (queue.max_queue_size) {
        return this.t('queueInfo', { active, max: queue.max_queue_size });
      }
      return this.t('queueFallback');
    },
    taskTitle() {
      if (this.task.status === 'running') {
        return this.t('taskRunning');
      }
      if (this.task.status === 'succeeded') {
        return this.t('taskSucceeded');
      }
      if (this.task.status === 'failed') {
        return this.t('taskFailed');
      }
      return this.t('recentPreview');
    },
    taskTagType() {
      if (this.task.status === 'succeeded') {
        return 'success';
      }
      if (this.task.status === 'failed') {
        return 'danger';
      }
      if (this.task.status === 'running') {
        return 'warning';
      }
      return 'info';
    },
    currentImage() {
      if (!this.result) {
        return null;
      }
      const image = this.result.images && this.result.images[0];
      if (!image) {
        return null;
      }
      return {
        ...image,
        width: this.result.width,
        height: this.result.height,
        seed: this.result.seed,
      };
    },
    recentImages() {
      return this.historyList.filter((item) => item.url).slice(0, 8);
    },
  },
  mounted() {
    this.refreshAll();
    this.analyzeSceneGraph();
  },
  beforeUnmount() {
    this.stopPolling();
  },
  methods: {
    t(key, params = {}) {
      const dict = I18N[this.lang] || I18N.zh;
      let text = dict[key] || I18N.zh[key] || key;
      Object.entries(params).forEach(([name, value]) => {
        text = text.replace(new RegExp(`\\{${name}\\}`, 'g'), String(value));
      });
      return text;
    },
    toggleLanguage() {
      this.lang = this.lang === 'zh' ? 'en' : 'zh';
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('landscape-ui-lang', this.lang);
      }
    },
    optionLabel(type, value) {
      const group = OPTION_LABELS[type] || {};
      const entry = group[value];
      return entry ? entry[this.lang] : value;
    },
    statusLabel(value) {
      const entry = STATUS_LABELS[value];
      return entry ? entry[this.lang] : (value || '-');
    },
    stageLabel(value) {
      const entry = STAGE_LABELS[value];
      return entry ? entry[this.lang] : (value || '-');
    },
    emptyGraphDraft() {
      return {
        entities: '',
        expanded_entities: '',
        attributes: '',
        relations: '',
        layout: '',
        style_hints: '',
        extracted_terms: '',
      };
    },
    particleStyle(index) {
      const left = (index * 37) % 100;
      const top = (index * 23) % 100;
      const delay = (index % 9) * -1.4;
      const duration = 10 + (index % 8);
      const height = 42 + (index % 5) * 18;
      return {
        left: `${left}%`,
        top: `${top}%`,
        height: `${height}px`,
        animationDelay: `${delay}s`,
        animationDuration: `${duration}s`,
      };
    },
    async refreshAll() {
      await Promise.all([this.checkHealth(), this.loadHistory(), this.loadTasks()]);
    },
    async checkHealth() {
      try {
        const { data } = await axios.get(`${API_BASE}/api/v1/health`);
        this.health = data || {};
        this.queueInfo = data.task_queue || { running: 0, queued: 0 };
        if (Array.isArray(data.styles) && data.styles.length) {
          this.styleOptions = data.styles;
        }
      } catch (error) {
        this.health = { status: 'offline' };
      }
    },
    async loadTasks() {
      try {
        const { data } = await axios.get(`${API_BASE}/api/v1/tasks`);
        this.taskRows = Array.isArray(data.items) ? data.items : [];
      } catch (error) {
        this.taskRows = this.task.id ? [this.task] : [];
      }
    },
    async loadHistory() {
      try {
        const { data } = await axios.get(`${API_BASE}/api/v1/history`);
        this.historyList = Array.isArray(data.items) ? data.items : [];
      } catch (error) {
        this.historyList = [];
      }
    },
    useSamplePrompt(text) {
      this.form.prompt = text;
      this.analyzeSceneGraph();
    },
    async analyzeSceneGraph() {
      if (!this.form.prompt.trim()) {
        return;
      }
      this.analyzing = true;
      this.errorMessage = '';
      try {
        const { data } = await axios.post(`${API_BASE}/api/v1/scene-graph`, {
          prompt: this.form.prompt,
        });
        this.sceneGraph = data;
        this.graphDraft = this.graphToDraft(data);
      } catch (error) {
        this.errorMessage = this.apiError(error, this.t('parseFailed'));
      } finally {
        this.analyzing = false;
      }
    },
    resetGraphDraft() {
      this.graphDraft = this.graphToDraft(this.sceneGraph || {});
    },
    graphToDraft(graph) {
      return {
        entities: this.joinList(graph.entities),
        expanded_entities: this.joinList(graph.expanded_entities),
        attributes: this.joinList(graph.attributes),
        relations: this.joinList(graph.relations, '\n'),
        layout: this.joinList(graph.layout, '\n'),
        style_hints: this.joinList(graph.style_hints),
        extracted_terms: this.joinList(graph.extracted_terms),
      };
    },
    draftToGraph() {
      return {
        method: '用户编辑场景结构',
        entities: this.splitList(this.graphDraft.entities),
        expanded_entities: this.splitList(this.graphDraft.expanded_entities),
        attributes: this.splitList(this.graphDraft.attributes),
        relations: this.splitList(this.graphDraft.relations),
        layout: this.splitList(this.graphDraft.layout),
        style_hints: this.splitList(this.graphDraft.style_hints),
        extracted_terms: this.splitList(this.graphDraft.extracted_terms),
      };
    },
    joinList(value, separator = '、') {
      if (!Array.isArray(value)) {
        return value ? String(value) : '';
      }
      return value.filter(Boolean).join(separator);
    },
    splitList(value) {
      return String(value || '')
        .split(/[、，,；;\n]/)
        .map((item) => item.trim())
        .filter(Boolean);
    },
    async startGeneration() {
      if (!this.form.prompt.trim()) {
        this.errorMessage = this.t('inputRequired');
        return;
      }
      this.activeView = 'studio';
      this.submitting = true;
      this.errorMessage = '';
      this.result = null;
      try {
        if (!this.sceneGraph) {
          await this.analyzeSceneGraph();
        }
        const payload = {
          ...this.form,
          scene_graph_override: this.draftToGraph(),
          return_base64: false,
        };
        const { data } = await axios.post(`${API_BASE}/api/v1/tasks`, payload);
        this.task = data;
        await this.loadTasks();
        this.pollTask(data.id);
      } catch (error) {
        this.errorMessage = this.apiError(error, this.t('submitFailed'));
      } finally {
        this.submitting = false;
      }
    },
    pollTask(taskId) {
      this.stopPolling();
      this.pollTimer = window.setInterval(async () => {
        try {
          const { data } = await axios.get(`${API_BASE}/api/v1/tasks/${taskId}`);
          this.task = data;
          if (data.status === 'succeeded') {
            this.result = this.taskToResult(data);
            this.stopPolling();
            await this.refreshAll();
          } else if (data.status === 'failed') {
            this.errorMessage = data.error || this.t('taskFailedHint');
            this.stopPolling();
            await this.refreshAll();
          }
        } catch (error) {
          this.errorMessage = this.apiError(error, this.t('taskFetchFailed'));
          this.stopPolling();
        }
      }, 1200);
    },
    stopPolling() {
      if (this.pollTimer) {
        window.clearInterval(this.pollTimer);
        this.pollTimer = null;
      }
    },
    taskToResult(task) {
      const result = task.result || {};
      return {
        status: 'succeeded',
        images: [
          {
            filename: result.filename,
            url: result.url,
            qrcode: result.qrcode,
          },
        ],
        width: result.width,
        height: result.height,
        elapsed_ms: result.elapsed_ms,
        seed: result.seed,
        style: task.style,
        scene_graph: task.scene_graph,
      };
    },
    previewHistory(item) {
      this.result = {
        status: 'succeeded',
        images: [{ filename: item.filename, url: item.url }],
        width: item.width,
        height: item.height,
        elapsed_ms: item.elapsed_ms,
        seed: item.seed,
        style: item.style,
        scene_graph: item.scene_graph,
      };
    },
    reuseRecord(item) {
      this.form.prompt = item.prompt || this.form.prompt;
      this.form.style = item.style || this.form.style;
      if (item.width) this.form.width = item.width;
      if (item.height) this.form.height = item.height;
      if (item.seed !== null && item.seed !== undefined) this.form.seed = item.seed;
      const params = item.params || {};
      if (params.composition) this.form.composition = params.composition;
      if (params.steps) this.form.steps = params.steps;
      if (params.guidance_scale !== null && params.guidance_scale !== undefined) this.form.guidance_scale = params.guidance_scale;
      if (params.detail_level !== null && params.detail_level !== undefined) this.form.detail_level = params.detail_level;
      if (params.blank_level !== null && params.blank_level !== undefined) this.form.blank_level = params.blank_level;
      if (params.negative_prompt) this.form.negative_prompt = params.negative_prompt;
      this.sceneGraph = item.scene_graph || null;
      this.graphDraft = this.graphToDraft(this.sceneGraph || {});
      this.previewHistory(item);
      this.activeView = 'studio';
    },
    toggleCompare(item) {
      const exists = this.compareList.some((current) => current.filename === item.filename);
      if (exists) {
        this.compareList = this.compareList.filter((current) => current.filename !== item.filename);
        return;
      }
      if (this.compareList.length >= 4) {
        this.compareList = [...this.compareList.slice(1), item];
        return;
      }
      this.compareList = [...this.compareList, item];
    },
    isInCompare(item) {
      return this.compareList.some((current) => current.filename === item.filename);
    },
    async deleteHistory(item) {
      try {
        await axios.delete(`${API_BASE}/api/v1/history/${item.filename}`);
        this.compareList = this.compareList.filter((current) => current.filename !== item.filename);
        await this.loadHistory();
      } catch (error) {
        this.errorMessage = this.apiError(error, this.t('deleteFailed'));
      }
    },
    openImage(url) {
      window.open(url, '_blank', 'noopener');
    },
    formatDate(value) {
      if (!value) {
        return '-';
      }
      return String(value).replace('T', ' ').slice(0, 16);
    },
    apiError(error, fallback) {
      const detail = error && error.response && error.response.data && error.response.data.detail;
      if (detail) {
        return typeof detail === 'string' ? detail : JSON.stringify(detail);
      }
      return fallback;
    },
  },
};
</script>

<style>
:root {
  --paper: #f3efe4;
  --paper-deep: #e8dfcf;
  --ink: #17231f;
  --muted: #6e766e;
  --line: rgba(31, 45, 40, 0.16);
  --green: #2f5d50;
  --green-dark: #1f4138;
  --cinnabar: #9d3f2e;
  --gold: #b99555;
  --panel: rgba(255, 252, 244, 0.84);
  --shadow: 0 24px 70px rgba(32, 42, 36, 0.15);
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  min-width: 320px;
  background: var(--paper);
  color: var(--ink);
  font-family: "Noto Serif SC", "Source Han Serif SC", "Microsoft YaHei", Arial, sans-serif;
}

button,
input,
textarea {
  font-family: inherit;
}

.app-shell {
  position: relative;
  min-height: 100vh;
  display: grid;
  grid-template-columns: 286px minmax(0, 1fr);
  overflow: hidden;
  background:
    linear-gradient(120deg, rgba(255, 255, 255, 0.7), rgba(232, 223, 207, 0.7)),
    radial-gradient(circle at 18% 12%, rgba(185, 149, 85, 0.2), transparent 28%),
    linear-gradient(150deg, #f8f4e9 0%, #e8dfcf 48%, #d7e1d8 100%);
}

.paper-texture {
  position: fixed;
  inset: 0;
  pointer-events: none;
  opacity: 0.42;
  background-image:
    repeating-linear-gradient(0deg, rgba(23, 35, 31, 0.026) 0 1px, transparent 1px 5px),
    repeating-linear-gradient(90deg, rgba(23, 35, 31, 0.018) 0 1px, transparent 1px 7px);
  mix-blend-mode: multiply;
}

.ink-field {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
}

.ink-stroke {
  position: absolute;
  width: 1px;
  border-radius: 999px;
  background: linear-gradient(180deg, transparent, rgba(47, 93, 80, 0.2), transparent);
  transform: rotate(18deg);
  animation: inkDrift 14s ease-in-out infinite;
}

@keyframes inkDrift {
  0% {
    opacity: 0;
    transform: translate3d(0, 22px, 0) rotate(18deg) scaleY(0.6);
  }
  35% {
    opacity: 0.75;
  }
  100% {
    opacity: 0;
    transform: translate3d(34px, -78px, 0) rotate(18deg) scaleY(1.2);
  }
}

.side-nav {
  position: relative;
  z-index: 2;
  min-height: 100vh;
  padding: 28px 22px;
  border-right: 1px solid rgba(31, 45, 40, 0.13);
  background: rgba(250, 246, 236, 0.74);
  backdrop-filter: blur(18px);
}

.brand-mark {
  display: flex;
  gap: 14px;
  align-items: center;
  margin-bottom: 36px;
}

.seal {
  width: 50px;
  height: 50px;
  display: grid;
  place-items: center;
  color: #fff9ec;
  background: var(--cinnabar);
  border-radius: 8px;
  font-size: 26px;
  font-weight: 700;
  box-shadow: 0 10px 24px rgba(157, 63, 46, 0.25);
}

.brand-mark h1 {
  margin: 0;
  font-size: 18px;
  line-height: 1.25;
  letter-spacing: 0;
}

.brand-mark p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}

.nav-list {
  display: grid;
  gap: 10px;
}

.nav-item {
  width: 100%;
  height: 48px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: transparent;
  color: #34423c;
  cursor: pointer;
  font-size: 15px;
  text-align: left;
  padding: 0 12px;
  transition: 0.2s ease;
}

.nav-item:hover,
.nav-item.active {
  background: rgba(47, 93, 80, 0.1);
  border-color: rgba(47, 93, 80, 0.18);
  color: var(--green-dark);
}

.nav-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  background: rgba(47, 93, 80, 0.1);
  font-weight: 700;
}

.nav-icon svg {
  stroke-width: 2;
}

.queue-tile {
  position: absolute;
  left: 22px;
  right: 22px;
  bottom: 24px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 252, 244, 0.7);
}

.queue-title {
  font-size: 13px;
  color: var(--muted);
}

.queue-numbers {
  display: flex;
  gap: 18px;
  margin: 10px 0 12px;
}

.queue-numbers span {
  color: var(--muted);
  font-size: 13px;
}

.queue-numbers b {
  margin-right: 5px;
  color: var(--ink);
  font-size: 22px;
}

.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--muted);
  font-size: 13px;
}

.status-dot::before {
  content: "";
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c5a457;
}

.status-dot.online::before {
  background: #3f8f65;
}

.workspace {
  position: relative;
  z-index: 1;
  min-width: 0;
  height: 100vh;
  overflow: auto;
  padding: 28px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.eyebrow,
.section-kicker {
  margin: 0 0 7px;
  color: var(--cinnabar);
  font-size: 12px;
  font-weight: 700;
}

.topbar h2,
.panel-heading h3,
.page-heading h3 {
  margin: 0;
  letter-spacing: 0;
}

.topbar h2 {
  font-size: clamp(26px, 4vw, 42px);
}

.top-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.icon-button.el-button > span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.icon-button svg {
  flex: 0 0 auto;
}

.studio-layout {
  display: grid;
  grid-template-columns: minmax(360px, 0.92fr) minmax(480px, 1.35fr);
  gap: 20px;
  align-items: start;
}

.output-column {
  display: grid;
  gap: 20px;
}

.panel,
.page-panel {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(18px);
}

.panel {
  padding: 20px;
}

.page-panel {
  min-height: calc(100vh - 116px);
  padding: 24px;
}

.panel-heading,
.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 18px;
}

.panel-heading h3,
.page-heading h3 {
  font-size: 20px;
}

.poem-input :deep(.el-textarea__inner) {
  min-height: 150px;
  border-radius: 8px;
  background: rgba(255, 253, 247, 0.82);
  font-size: 16px;
  line-height: 1.8;
}

.quick-prompts {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin: 14px 0 18px;
}

.quick-prompts button {
  border: 1px solid rgba(47, 93, 80, 0.18);
  border-radius: 999px;
  background: rgba(47, 93, 80, 0.07);
  color: var(--green-dark);
  padding: 6px 12px;
  cursor: pointer;
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.control-block {
  display: grid;
  gap: 8px;
}

.control-block.full {
  margin-top: 14px;
}

.control-block > span,
.graph-editor span,
.slider-title {
  color: #4f5a54;
  font-size: 13px;
  font-weight: 700;
}

.slider-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-top: 16px;
  padding: 16px 14px 8px;
  border: 1px solid rgba(47, 93, 80, 0.12);
  border-radius: 8px;
  background: rgba(47, 93, 80, 0.045);
}

.slider-title {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.main-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.task-progress {
  padding: 14px;
  margin-bottom: 16px;
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 8px;
  background: rgba(47, 93, 80, 0.055);
}

.progress-meta,
.progress-steps {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.progress-meta {
  margin-bottom: 9px;
  font-size: 14px;
}

.progress-steps {
  margin-top: 10px;
  color: var(--muted);
  font-size: 12px;
}

.progress-steps span.done {
  color: var(--green-dark);
  font-weight: 700;
}

.error-alert {
  margin-bottom: 14px;
}

.image-stage {
  position: relative;
  overflow: hidden;
  border-radius: 8px;
  background: #141b18;
}

.image-stage img {
  display: block;
  width: 100%;
  max-height: 62vh;
  object-fit: contain;
}

.image-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
  padding: 10px;
  color: #fff8e8;
  background: rgba(18, 24, 21, 0.72);
}

.showcase-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.showcase-item {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 3;
  border: 0;
  border-radius: 8px;
  background: #e7dfd1;
  cursor: pointer;
  padding: 0;
}

.showcase-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.25s ease;
}

.showcase-item:hover img {
  transform: scale(1.04);
}

.showcase-item span {
  position: absolute;
  left: 8px;
  bottom: 8px;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(255, 252, 244, 0.8);
  color: var(--green-dark);
  font-size: 12px;
}

.empty-showcase {
  min-height: 340px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 20px;
  color: var(--muted);
  text-align: center;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.28), rgba(47, 93, 80, 0.08)),
    repeating-linear-gradient(135deg, rgba(47, 93, 80, 0.04) 0 1px, transparent 1px 12px);
  border-radius: 8px;
}

.mountain-line {
  width: min(420px, 80%);
  height: 120px;
  clip-path: polygon(0 78%, 14% 58%, 22% 67%, 39% 30%, 57% 74%, 68% 52%, 82% 69%, 100% 42%, 100% 100%, 0 100%);
  background: linear-gradient(90deg, rgba(47, 93, 80, 0.72), rgba(23, 35, 31, 0.36));
}

.chapter-flow {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.chapter-flow article {
  border: 1px solid rgba(47, 93, 80, 0.14);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 252, 244, 0.68);
}

.chapter-flow span {
  color: var(--cinnabar);
  font-size: 12px;
  font-weight: 700;
}

.chapter-flow strong {
  display: block;
  margin: 6px 0;
}

.chapter-flow p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

.graph-editor {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.graph-editor label {
  display: grid;
  gap: 6px;
}

.history-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 16px;
}

.history-card,
.compare-card,
.status-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: rgba(255, 252, 244, 0.72);
  overflow: hidden;
}

.history-card img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
}

.history-body {
  padding: 13px;
}

.history-title {
  min-height: 42px;
  font-weight: 700;
  line-height: 1.45;
}

.history-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  margin: 8px 0 12px;
  color: var(--muted);
  font-size: 12px;
}

.history-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.compare-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(310px, 1fr));
  gap: 18px;
}

.compare-card img {
  width: 100%;
  aspect-ratio: 4 / 3;
  object-fit: cover;
  display: block;
  background: #ded5c7;
}

.compare-card > div {
  padding: 14px;
}

.compare-card h4 {
  margin: 0 0 8px;
}

.compare-card p {
  min-height: 44px;
  margin: 0 0 12px;
  color: var(--muted);
  line-height: 1.55;
}

.compare-card dl {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  margin: 0;
  gap: 8px;
}

.compare-card dl div {
  padding: 8px;
  border-radius: 8px;
  background: rgba(47, 93, 80, 0.07);
}

.compare-card dt {
  color: var(--muted);
  font-size: 12px;
}

.compare-card dd {
  margin: 4px 0 0;
  font-weight: 700;
}

.compare-empty {
  min-height: 420px;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 16px;
  color: var(--muted);
  text-align: center;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.status-card {
  padding: 16px;
}

.status-card span {
  color: var(--muted);
  font-size: 13px;
}

.status-card strong {
  display: block;
  margin: 9px 0;
  font-size: 24px;
}

.status-card p {
  margin: 0;
  color: var(--muted);
  line-height: 1.6;
}

.queue-table {
  margin-top: 18px;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: rgba(255, 252, 244, 0.7);
}

.table-head,
.table-row {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr 1fr 0.6fr;
  gap: 12px;
  padding: 12px 14px;
  align-items: center;
}

.table-head {
  background: rgba(47, 93, 80, 0.1);
  color: var(--green-dark);
  font-weight: 700;
}

.table-row {
  border-top: 1px solid var(--line);
}

.table-empty {
  padding: 24px;
  color: var(--muted);
  text-align: center;
}

.el-button--primary {
  --el-button-bg-color: var(--green);
  --el-button-border-color: var(--green);
  --el-button-hover-bg-color: var(--green-dark);
  --el-button-hover-border-color: var(--green-dark);
}

.el-radio-button__inner {
  border-color: rgba(47, 93, 80, 0.18);
}

.el-radio-button__original-radio:checked + .el-radio-button__inner {
  background: var(--green);
  border-color: var(--green);
  box-shadow: -1px 0 0 0 var(--green);
}

.el-slider__bar {
  background: var(--green);
}

.el-slider__button {
  border-color: var(--green);
}

@media (max-width: 1180px) {
  .app-shell {
    grid-template-columns: 1fr;
  }

  .side-nav {
    min-height: auto;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 14px;
    padding: 16px;
  }

  .brand-mark {
    margin-bottom: 0;
  }

  .nav-list {
    grid-auto-flow: column;
    align-items: center;
    overflow-x: auto;
  }

  .queue-tile {
    display: none;
  }

  .workspace {
    height: auto;
    min-height: calc(100vh - 92px);
  }

  .studio-layout {
    grid-template-columns: 1fr;
  }

  .status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .workspace {
    padding: 16px;
  }

  .topbar,
  .panel-heading,
  .page-heading {
    flex-direction: column;
    align-items: stretch;
  }

  .side-nav {
    grid-template-columns: 1fr;
  }

  .nav-list {
    grid-auto-flow: row;
  }

  .control-grid,
  .slider-row,
  .chapter-flow,
  .graph-editor,
  .status-grid,
  .showcase-grid {
    grid-template-columns: 1fr;
  }

  .table-head,
  .table-row {
    grid-template-columns: 1fr;
  }
}
</style>
