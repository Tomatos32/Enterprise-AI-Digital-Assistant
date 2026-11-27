<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-6 lg:p-8 transition-colors duration-180">
    <div class="max-w-6xl w-full mx-auto space-y-6 pb-10">
      <!-- Top Header & Actions -->
      <header class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-start sm:items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-bg-surface border border-border-card flex items-center justify-center text-text-main shrink-0">
            <ListTodo class="w-5 h-5" />
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">知识库运维与异步任务</h1>
              <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-surface text-text-secondary border border-border-subtle inline-flex items-center gap-1">
                <ShieldCheck class="w-3 h-3" />
                <span>管理员专属</span>
              </span>
              <StatusMark
                :status="qdrantHealthStatus"
                :label="qdrantHealthLabel"
              />
            </div>
            <p class="text-xs text-text-muted mt-0.5">
              管理多格式制度入库解析、异步任务进度与全库向量索引同步
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <FuseButton
            variant="secondary"
            size="md"
            :loading="isRefreshing"
            :disabled="isUploading || isSyncing"
            @click="refreshAllData"
          >
            <span class="inline-flex items-center gap-1.5">
              <RefreshCw class="w-3.5 h-3.5 text-text-secondary" :class="{ 'animate-spin': isRefreshing }" />
              <span>{{ isRefreshing ? '刷新中...' : '刷新状态' }}</span>
            </span>
          </FuseButton>

          <router-link
            to="/knowledge"
            class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
          >
            <BookOpen class="w-3.5 h-3.5 text-text-secondary" />
            <span>制度阅读库</span>
          </router-link>

          <router-link
            to="/"
            class="btn-secondary px-3 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1.5 cursor-pointer"
          >
            <MessageSquare class="w-3.5 h-3.5 text-text-secondary" />
            <span>返回对话</span>
          </router-link>
        </div>
      </header>

      <!-- Feedback Banner -->
      <transition name="banner-slide">
        <div
          v-if="feedback.message"
          role="status"
          class="px-4 py-3 rounded-xl border flex items-start justify-between gap-3 text-xs bg-bg-surface"
          :class="feedbackBannerClass"
        >
          <div class="flex items-start gap-2.5">
            <CheckCircle2 v-if="feedback.type === 'success'" class="w-4 h-4 text-status-success shrink-0 mt-0.5" />
            <span
              v-else
              class="w-2 h-2 rounded-full shrink-0 mt-1.5"
              :class="feedback.type === 'warning' ? 'bg-status-approval' : 'bg-status-danger'"
            ></span>
            <span class="leading-relaxed font-medium">{{ feedback.message }}</span>
          </div>
          <button
            type="button"
            @click="feedback.message = ''"
            class="p-1 rounded-md text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer shrink-0 transition-colors duration-150"
            title="关闭提示"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </transition>

      <!-- Section 1: Knowledge Base Vector Telemetry Overview -->
      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Card A: Qdrant Mode -->
        <div class="rounded-xl bg-bg-card border border-border-card p-4 sm:p-5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-text-muted">Qdrant 运行底座</span>
            <Database class="w-4 h-4 text-text-muted" />
          </div>
          <div class="text-sm font-semibold text-text-main truncate">{{ qdrantModeText }}</div>
          <div class="text-[11px] text-text-secondary truncate font-mono" :title="kbStatus.storage_location">
            {{ kbStatus.collection_name || 'enterprise_knowledge' }} · {{ kbStatus.storage_location || '本地持久化' }}
          </div>
        </div>

        <!-- Card B: Vector Points -->
        <div class="rounded-xl bg-bg-card border border-border-card p-4 sm:p-5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-text-muted">向量切片点位</span>
            <Layers class="w-4 h-4 text-text-muted" />
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-semibold text-text-main font-mono tabular-nums">
              {{ Number(kbStatus.points_count || 0).toLocaleString() }}
            </span>
            <span class="text-[11px] text-status-success font-medium">
              {{ kbStatus.collection_exists ? '已就绪' : '待构建' }}
            </span>
          </div>
          <div class="text-[11px] text-text-muted">
            稠密向量 + BM25 混合检索
          </div>
        </div>

        <!-- Card C: Embedding Engine & Dimension -->
        <div class="rounded-xl bg-bg-card border border-border-card p-4 sm:p-5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-text-muted">向量维度与引擎</span>
            <Cpu class="w-4 h-4 text-text-muted" />
          </div>
          <div class="text-sm font-semibold text-text-main font-mono tabular-nums">
            {{ kbStatus.vector_size || 1024 }} 维 · {{ embeddingEngineName }}
          </div>
          <div class="text-[11px] text-text-secondary truncate" :title="embeddingModelName">
            模型: <span class="font-mono">{{ embeddingModelName }}</span>
          </div>
        </div>

        <!-- Card D: Documents Count -->
        <div class="rounded-xl bg-bg-card border border-border-card p-4 sm:p-5 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-[11px] font-medium text-text-muted">已收录文档</span>
            <FolderOpen class="w-4 h-4 text-text-muted" />
          </div>
          <div class="flex items-baseline gap-2">
            <span class="text-xl font-semibold text-text-main font-mono tabular-nums">
              {{ kbStatus.total_documents_count || docsInventory.total_count || 0 }}
            </span>
            <span class="text-[11px] text-text-secondary">篇制度</span>
          </div>
          <div class="text-[11px] text-text-muted tabular-nums">
            内置 {{ kbStatus.sample_kb_file_count || 0 }} · 上传 {{ kbStatus.uploaded_file_count || 0 }}
          </div>
        </div>
      </section>

      <!-- Section 2 & 3: Upload Zone + Sync Operations -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left 7 Cols: Drag & Drop Multi-Format Upload & Mode Toggle -->
        <section class="lg:col-span-7 rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-5">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                <Upload class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-semibold text-text-main">多格式知识文档上传</h2>
                <p class="text-[11px] text-text-muted">.md / .pdf / .xlsx / .xls / .txt · 单文件上限 20 MB</p>
              </div>
            </div>

            <div class="flex items-center gap-1.5">
              <RubberSegment
                v-model="uploadMode"
                :options="uploadModeOptions"
              />
              <WarmTooltip
                :content="uploadMode === 'async' ? '优先投递 Celery 队列，Broker 离线时自动降级后台执行' : '立即解析切分并同步刷新索引'"
                position="top"
              >
                <span class="w-6 h-6 rounded-md inline-flex items-center justify-center text-text-muted hover:text-text-main cursor-help">
                  <Info class="w-3.5 h-3.5" />
                </span>
              </WarmTooltip>
            </div>
          </div>

          <!-- Dropzone Area -->
          <div
            @dragover.prevent="isDragOver = true"
            @dragleave.prevent="isDragOver = false"
            @drop.prevent="handleFileDrop"
            @click="triggerFilePicker"
            class="relative rounded-xl border border-dashed p-6 sm:p-7 text-center transition-colors duration-150 cursor-pointer"
            :class="
              isDragOver
                ? 'border-border-focus bg-bg-hover'
                : 'border-border-card bg-bg-surface hover:border-border-strong'
            "
          >
            <input
              ref="fileInputRef"
              type="file"
              multiple
              accept=".md,.pdf,.xlsx,.xls,.txt"
              class="hidden"
              @change="handleFileSelected"
            />
            <div class="flex flex-col items-center gap-2.5">
              <div
                class="w-10 h-10 rounded-xl flex items-center justify-center border transition-colors duration-150"
                :class="
                  isDragOver
                    ? 'bg-action-primary text-action-primary-fg border-action-primary'
                    : 'bg-bg-card text-text-main border-border-card'
                "
              >
                <Upload class="w-4 h-4" />
              </div>
              <div class="space-y-1">
                <p class="text-xs sm:text-sm font-medium text-text-main">
                  拖拽制度文档到此处，或 <span class="underline underline-offset-2">点击浏览本地文件</span>
                </p>
                <p class="text-[11px] text-text-muted">
                  支持 Markdown、PDF、Excel 及纯文本；后端强制执行路径与后缀校验
                </p>
              </div>
            </div>
          </div>

          <!-- Category Selector -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <label class="text-xs font-semibold text-text-main">业务领域分类</label>
              <span class="text-[11px] text-text-muted">用于领域检索过滤</span>
            </div>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="cat in categoryOptions"
                :key="cat.value"
                type="button"
                @click="selectedCategory = cat.value"
                class="btn-pressable px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer"
                :class="
                  selectedCategory === cat.value
                    ? 'bg-action-primary text-action-primary-fg border-action-primary'
                    : 'bg-bg-surface text-text-secondary border-border-subtle hover:text-text-main hover:border-border-card'
                "
              >
                {{ cat.label }}
              </button>
            </div>
          </div>

          <!-- Queued Files Preview -->
          <div v-if="queuedFiles.length > 0" class="space-y-2">
            <div class="flex items-center justify-between text-xs">
              <span class="font-semibold text-text-main">待提交队列 ({{ queuedFiles.length }})</span>
              <button
                type="button"
                @click="queuedFiles = []"
                class="text-[11px] text-text-muted hover:text-status-danger cursor-pointer transition-colors duration-150"
              >
                清空队列
              </button>
            </div>
            <div class="space-y-1.5 max-h-40 overflow-y-auto pr-1">
              <div
                v-for="(item, idx) in queuedFiles"
                :key="item.key"
                class="px-3 py-2 rounded-lg bg-bg-surface border border-border-subtle flex items-center justify-between gap-2 text-xs"
              >
                <div class="flex items-center gap-2.5 min-w-0">
                  <component :is="resolveFormatIcon(item.ext)" class="w-4 h-4 text-text-secondary shrink-0" />
                  <span class="font-medium text-text-main truncate">{{ item.file.name }}</span>
                  <span class="text-[10px] font-mono tabular-nums text-text-muted shrink-0">{{ formatBytes(item.file.size) }}</span>
                </div>
                <button
                  type="button"
                  @click="removeQueuedFile(idx)"
                  class="p-1 rounded-md text-text-muted hover:text-status-danger cursor-pointer shrink-0 transition-colors duration-150"
                  title="移出队列"
                >
                  <Trash2 class="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          <!-- Submit Action Footer -->
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-border-subtle">
            <div class="text-[11px] text-text-muted flex items-center gap-1.5">
              <Zap v-if="uploadMode === 'sync'" class="w-3.5 h-3.5 text-text-secondary shrink-0" />
              <Clock v-else class="w-3.5 h-3.5 text-text-secondary shrink-0" />
              <span>
                {{
                  uploadMode === 'sync'
                    ? '同步模式：即时切片入库并刷新混合检索'
                    : '异步模式：Celery 或本地后台队列非阻塞执行'
                }}
              </span>
            </div>

            <FuseButton
              variant="primary"
              size="lg"
              :loading="isUploading"
              :disabled="queuedFiles.length === 0 || isSyncing"
              @click="submitUploadQueue"
            >
              <span class="inline-flex items-center gap-1.5">
                <Upload class="w-3.5 h-3.5" />
                <span>
                  {{
                    isUploading
                      ? '正在提交...'
                      : uploadMode === 'async'
                        ? '提交异步解析'
                        : '上传并立即入库'
                  }}
                </span>
              </span>
            </FuseButton>
          </div>
        </section>

        <!-- Right 5 Cols: Full / Incremental Sync Control Card -->
        <section class="lg:col-span-5 rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 flex flex-col justify-between space-y-5">
          <div class="space-y-4">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                <RefreshCw class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-semibold text-text-main">索引同步与重建</h2>
                <p class="text-[11px] text-text-muted">联动内置与上传文档刷新 Qdrant 及 BM25</p>
              </div>
            </div>

            <!-- Incremental Sync Block -->
            <div class="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-3">
              <div>
                <h3 class="text-xs font-semibold text-text-main">增量校验同步 (Sync)</h3>
                <p class="text-[11px] text-text-muted mt-0.5 leading-relaxed">
                  基于内容指纹执行幂等向量写入，补齐新增切片并刷新检索，不影响在线服务。
                </p>
              </div>

              <div v-if="confirmSyncMode !== 'incremental'">
                <FuseButton
                  variant="secondary"
                  size="md"
                  :loading="isSyncing && activeSyncRecreate === false"
                  :disabled="isSyncing || isUploading"
                  customClass="w-full"
                  @click="confirmSyncMode = 'incremental'"
                >
                  <span class="inline-flex items-center gap-1.5">
                    <RefreshCw class="w-3.5 h-3.5 text-text-secondary" />
                    <span>执行增量同步 (Sync)</span>
                  </span>
                </FuseButton>
              </div>

              <div
                v-else
                class="p-2.5 rounded-lg bg-bg-card border border-border-strong flex items-center justify-between gap-2"
              >
                <span class="text-[11px] font-medium text-text-main">
                  确认扫描全部制度并同步？
                </span>
                <div class="flex items-center gap-1.5 shrink-0">
                  <button
                    type="button"
                    :disabled="isSyncing"
                    @click="executeKnowledgeSync(false)"
                    class="btn-primary px-2.5 py-1 rounded-md text-[11px] font-medium cursor-pointer disabled:opacity-50"
                  >
                    确认
                  </button>
                  <button
                    type="button"
                    @click="confirmSyncMode = ''"
                    class="px-2 py-1 rounded-md text-[11px] text-text-secondary hover:text-text-main cursor-pointer"
                  >
                    取消
                  </button>
                </div>
              </div>
            </div>

            <!-- Recreate Rebuild Block (Hold-to-Confirm Protection) -->
            <div class="p-4 rounded-lg bg-bg-surface border border-status-danger/30 space-y-3">
              <div>
                <h3 class="text-xs font-semibold text-status-danger flex items-center gap-1.5">
                  <RotateCcw class="w-3.5 h-3.5" />
                  <span>全量清空重建索引 (Recreate)</span>
                </h3>
                <p class="text-[11px] text-text-muted mt-0.5 leading-relaxed">
                  删除并重建 Qdrant 向量集合，全量重新向量化全部文档，清除过期碎片。
                </p>
              </div>

              <HoldButton
                label="长按全量重建索引"
                holding-label="继续按住以重建集合..."
                hint="高危操作：长按 0.85 秒触发全量重建"
                variant="danger"
                size="md"
                :loading="isSyncing && activeSyncRecreate === true"
                :disabled="isSyncing || isUploading"
                class="w-full"
                @confirm="executeKnowledgeSync(true)"
              >
                <template #icon>
                  <RotateCcw class="w-3.5 h-3.5" />
                </template>
              </HoldButton>
            </div>
          </div>

          <!-- Latest Sync Summary -->
          <div
            v-if="lastSyncReport"
            class="p-3.5 rounded-lg bg-bg-surface border border-border-card space-y-1.5 text-[11px]"
          >
            <div class="flex items-center justify-between font-semibold text-status-success">
              <span>最近一次同步结果</span>
              <span class="font-mono tabular-nums">{{ lastSyncReport.elapsed_seconds ?? 0 }}s</span>
            </div>
            <div class="text-text-secondary tabular-nums">
              内置切片: <span class="font-mono font-semibold text-text-main">{{ lastSyncReport.chunks_indexed ?? 0 }}</span> ·
              上传重索引: <span class="font-mono font-semibold text-text-main">{{ lastSyncReport.uploaded_reindexed_files ?? 0 }} 篇</span> ·
              总点位: <span class="font-mono font-semibold text-text-main">{{ lastSyncReport.qdrant_info?.points_count ?? 0 }}</span>
            </div>
          </div>
        </section>
      </div>

      <!-- Section 4: Real-Time Task Progress Tracking List -->
      <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-4">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
              <Clock class="w-4 h-4" />
            </div>
            <div>
              <div class="flex items-center gap-2">
                <h2 class="text-sm font-semibold text-text-main">入库与异步任务进度</h2>
                <StatusMark
                  v-if="activeTaskCount > 0"
                  status="running"
                  :label="`轮询中 (${activeTaskCount})`"
                />
                <StatusMark
                  v-else
                  status="idle"
                  label="无排队任务"
                />
              </div>
              <p class="text-[11px] text-text-muted">
                实时追踪排队、解析、切片与向量入库状态
              </p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-1.5 text-[11px]">
            <button
              v-for="tab in taskFilterTabs"
              :key="tab.value"
              type="button"
              @click="taskFilter = tab.value"
              class="btn-pressable px-2.5 py-1 rounded-md border font-medium cursor-pointer tabular-nums"
              :class="
                taskFilter === tab.value
                  ? 'bg-action-primary text-action-primary-fg border-action-primary'
                  : 'bg-bg-surface text-text-secondary border-border-subtle hover:text-text-main hover:border-border-card'
              "
            >
              {{ tab.label }} ({{ tab.count }})
            </button>
          </div>
        </div>

        <div v-if="filteredTasks.length === 0" class="py-10 text-center text-xs text-text-muted border border-dashed border-border-subtle rounded-xl">
          暂无匹配的任务记录
        </div>

        <div v-else class="space-y-3">
          <div
            v-for="task in filteredTasks"
            :key="task.task_id"
            class="p-4 rounded-xl bg-bg-surface border border-border-subtle space-y-3"
          >
            <!-- Task Top Row -->
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-2">
              <div class="flex flex-wrap items-center gap-2 min-w-0">
                <StatusMark :status="mapTaskStatusToMark(task.status)" />
                <span class="text-xs sm:text-sm font-semibold text-text-main truncate">
                  {{ task.filename || task.task_id }}
                </span>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-mono bg-bg-card border border-border-subtle text-text-secondary">
                  {{ task.task_id }}
                </span>
                <span
                  v-if="task.category"
                  class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-card text-text-main border border-border-card"
                >
                  {{ task.category }}
                </span>
                <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-card border border-border-subtle text-text-muted">
                  {{ formatExecutionMode(task.execution_mode) }}
                </span>
              </div>

              <div class="flex items-center gap-3 text-[11px] text-text-muted shrink-0">
                <span>操作人: <strong class="text-text-secondary">{{ task.uploader || 'admin' }}</strong></span>
                <span class="font-mono tabular-nums">{{ formatTime(task.updated_at || task.created_at) }}</span>
              </div>
            </div>

            <!-- Progress Bar & Message -->
            <div class="space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="text-text-secondary font-medium">{{ task.message || task.stage_label || '处理中...' }}</span>
                <span class="font-mono tabular-nums font-semibold text-text-main">{{ task.progress?.current ?? 0 }}%</span>
              </div>
              <div class="w-full h-1.5 rounded-full bg-bg-card border border-border-subtle overflow-hidden">
                <div
                  class="h-full rounded-full transition-[width] duration-300"
                  :class="progressBarColor(task.status)"
                  :style="{ width: `${Math.min(100, Math.max(0, task.progress?.current ?? 0))}%` }"
                ></div>
              </div>
              <p
                v-if="task.fallback_reason"
                class="text-[11px] text-status-approval flex items-center gap-1"
              >
                <Info class="w-3 h-3 shrink-0" />
                <span>{{ task.fallback_reason }}</span>
              </p>
              <p
                v-if="task.error"
                class="text-[11px] text-status-danger font-medium"
              >
                异常详情: {{ task.error }}
              </p>
            </div>

            <!-- 5-Stage Pipeline Steps with StatusMark -->
            <div class="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
              <div
                v-for="step in resolveTaskSteps(task)"
                :key="step.key"
                class="px-2.5 py-1.5 rounded-lg bg-bg-card border border-border-subtle flex items-center justify-between gap-1.5"
              >
                <StatusMark :status="step.status" :label="step.label" size="sm" />
                <Check v-if="step.status === 'success'" class="w-3 h-3 text-status-success shrink-0" />
              </div>
            </div>

            <!-- Result Telemetry Chips -->
            <div
              v-if="task.result && task.status === 'SUCCESS'"
              class="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-text-secondary"
            >
              <span
                v-if="task.result.chunks_indexed !== undefined"
                class="px-2 py-0.5 rounded-md bg-bg-card text-status-success border border-border-subtle font-mono tabular-nums"
              >
                入库切片: {{ task.result.chunks_indexed }} 条
              </span>
              <span
                v-if="task.size_bytes || task.result.size_bytes"
                class="px-2 py-0.5 rounded-md bg-bg-card border border-border-subtle font-mono tabular-nums"
              >
                体积: {{ formatBytes(task.size_bytes || task.result.size_bytes) }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <!-- Section 5: Indexed Documents Inventory Table -->
      <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-4">
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
              <FileText class="w-4 h-4" />
            </div>
            <div>
              <h2 class="text-sm font-semibold text-text-main">已索引知识文档台账</h2>
              <p class="text-[11px] text-text-muted">内置标准制度库与管理员上传文档</p>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <div class="relative">
              <Search class="w-3.5 h-3.5 text-text-muted absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                v-model.trim="docSearchQuery"
                type="text"
                placeholder="筛选文件名或分类..."
                class="pl-8 pr-3 py-1.5 rounded-lg bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus w-48 sm:w-56 transition-colors duration-150"
              />
            </div>

            <div class="flex items-center gap-1">
              <button
                v-for="src in docSourceTabs"
                :key="src.value"
                type="button"
                @click="docSourceFilter = src.value"
                class="btn-pressable px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer"
                :class="
                  docSourceFilter === src.value
                    ? 'bg-action-primary text-action-primary-fg border-action-primary'
                    : 'bg-bg-surface text-text-secondary border-border-subtle hover:text-text-main hover:border-border-card'
                "
              >
                {{ src.label }}
              </button>
            </div>
          </div>
        </div>

        <div class="overflow-x-auto rounded-lg border border-border-subtle">
          <table class="w-full text-left border-collapse text-xs">
            <thead>
              <tr class="bg-bg-surface text-[11px] text-text-secondary border-b border-border-subtle">
                <th class="py-2.5 px-3.5 font-semibold">文档名称</th>
                <th class="py-2.5 px-3 font-semibold">来源类型</th>
                <th class="py-2.5 px-3 font-semibold">业务分类</th>
                <th class="py-2.5 px-3 font-semibold">格式 / 体积</th>
                <th class="py-2.5 px-3 font-semibold">切片 / 方式</th>
                <th class="py-2.5 px-3 font-semibold">索引状态</th>
                <th class="py-2.5 px-3 font-semibold">最近更新</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border-subtle">
              <tr v-if="filteredDocuments.length === 0">
                <td colspan="7" class="py-8 text-center text-text-muted">
                  暂无匹配的已索引文档
                </td>
              </tr>
              <tr
                v-for="doc in filteredDocuments"
                :key="`${doc.source_type}-${doc.relative_path}`"
                class="hover:bg-bg-hover/60 transition-colors duration-150"
              >
                <td class="py-2.5 px-3.5">
                  <div class="flex items-center gap-2 min-w-[180px]">
                    <component :is="resolveFormatIcon(doc.format)" class="w-4 h-4 text-text-secondary shrink-0" />
                    <div class="min-w-0">
                      <div class="font-semibold text-text-main truncate max-w-[260px]" :title="doc.filename">
                        {{ doc.filename }}
                      </div>
                      <div class="text-[10px] text-text-muted font-mono truncate max-w-[260px]">
                        {{ doc.relative_path }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-surface border border-border-subtle text-text-secondary">
                    {{ doc.source_type === 'uploaded' ? '管理员上传' : '内置标准库' }}
                  </span>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <span class="px-2 py-0.5 rounded-md text-[10px] font-mono bg-bg-surface border border-border-subtle text-text-main">
                    {{ doc.category || 'GENERAL' }}
                  </span>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap font-mono tabular-nums text-[11px] text-text-secondary">
                  .{{ doc.format }} · {{ formatBytes(doc.size_bytes) }}
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap text-[11px] text-text-secondary tabular-nums">
                  <span v-if="doc.chunks_indexed !== null && doc.chunks_indexed !== undefined" class="font-mono font-semibold text-text-main">
                    {{ doc.chunks_indexed }} 片
                  </span>
                  <span v-else class="text-text-muted">基线切片</span>
                  <span class="text-text-muted"> · {{ formatExecutionMode(doc.execution_mode) }}</span>
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap">
                  <StatusMark :status="doc.status === 'FAILED' ? 'danger' : 'success'" :label="doc.status || 'INDEXED'" size="sm" />
                </td>
                <td class="py-2.5 px-3 whitespace-nowrap font-mono tabular-nums text-[11px] text-text-muted">
                  {{ formatTime(doc.updated_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import {
  ListTodo,
  ShieldCheck,
  RefreshCw,
  BookOpen,
  MessageSquare,
  CheckCircle2,
  X,
  Database,
  Layers,
  Cpu,
  FolderOpen,
  Upload,
  FileText,
  FileSpreadsheet,
  File,
  Trash2,
  Zap,
  Clock,
  Check,
  Search,
  RotateCcw,
  Info,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import FuseButton from '../components/ui/FuseButton.vue';
import HoldButton from '../components/ui/HoldButton.vue';
import RubberSegment from '../components/ui/RubberSegment.vue';
import StatusMark from '../components/ui/StatusMark.vue';
import WarmTooltip from '../components/ui/WarmTooltip.vue';

const ALLOWED_EXTENSIONS = ['.md', '.pdf', '.xlsx', '.xls', '.txt'];
const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const ACTIVE_STATUSES = new Set(['PENDING', 'PROGRESS', 'STARTED', 'RETRY']);

const router = useRouter();
const authStore = useAuthStore();

const fileInputRef = ref(null);
const isDragOver = ref(false);
const isRefreshing = ref(false);
const isUploading = ref(false);
const isSyncing = ref(false);
const activeSyncRecreate = ref(false);
const confirmSyncMode = ref('');

const uploadMode = ref('async');
const selectedCategory = ref('AUTO');
const queuedFiles = ref([]);
const taskFilter = ref('ALL');
const docSourceFilter = ref('ALL');
const docSearchQuery = ref('');

const kbStatus = reactive({
  status: 'healthy',
  client_mode: 'local_storage',
  storage_location: '',
  collection_name: 'enterprise_knowledge',
  collection_exists: true,
  points_count: 0,
  vector_size: 1024,
  embedding_engine: null,
  sample_kb_file_count: 0,
  uploaded_file_count: 0,
  total_documents_count: 0,
});

const docsInventory = reactive({
  documents: [],
  total_count: 0,
  builtin_count: 0,
  uploaded_count: 0,
  category_breakdown: {},
});

const taskList = ref([]);
const lastSyncReport = ref(null);

const feedback = reactive({
  type: 'success',
  message: '',
});

let pollTimer = null;

const uploadModeOptions = [
  { value: 'sync', label: '同步快速入库', icon: Zap },
  { value: 'async', label: 'Celery 异步入库', icon: Clock },
];

const categoryOptions = [
  { value: 'AUTO', label: '自动识别' },
  { value: 'HR', label: '行政人事 (HR)' },
  { value: 'PROCUREMENT', label: '采购审批 (PROC)' },
  { value: 'FINANCE', label: '财务报销 (FIN)' },
  { value: 'IT', label: 'IT 运维 (IT)' },
  { value: 'SECURITY', label: '安全合规 (SEC)' },
  { value: 'CS', label: '客户服务 (CS)' },
  { value: 'GENERAL', label: '通用制度' },
];

const docSourceTabs = [
  { value: 'ALL', label: '全部文档' },
  { value: 'uploaded', label: '管理员上传' },
  { value: 'builtin', label: '内置标准库' },
];

const qdrantHealthStatus = computed(() => {
  if (isRefreshing.value) return 'running';
  if (kbStatus.status === 'healthy') return 'success';
  return 'warning';
});

const qdrantHealthLabel = computed(() => {
  const modeLabel = qdrantModeText.value;
  return `${modeLabel} · ${Number(kbStatus.points_count || 0)} 切片`;
});

const qdrantModeText = computed(() => {
  const mode = kbStatus.client_mode;
  if (mode === 'remote_server') return '远程 Qdrant 集群';
  if (mode === 'local_storage') return '本地持久化 Qdrant';
  if (mode === 'in_memory') return '内存隔离模式';
  return mode || '本地向量底座';
});

const embeddingEngineName = computed(() => {
  const eng = kbStatus.embedding_engine || {};
  return eng.provider || 'local_semantic';
});

const embeddingModelName = computed(() => {
  const eng = kbStatus.embedding_engine || {};
  return eng.model || 'local-semantic-ngram-v1';
});

const feedbackBannerClass = computed(() => {
  if (feedback.type === 'success') {
    return 'border-border-strong text-text-main';
  }
  if (feedback.type === 'warning') {
    return 'border-status-approval/40 text-status-approval';
  }
  return 'border-status-danger/40 text-status-danger';
});

const activeTasks = computed(() => {
  return taskList.value.filter((t) => ACTIVE_STATUSES.has(String(t.status || '').toUpperCase()));
});

const activeTaskCount = computed(() => activeTasks.value.length);

const taskFilterTabs = computed(() => {
  const all = taskList.value;
  const running = all.filter((t) => ACTIVE_STATUSES.has(String(t.status || '').toUpperCase())).length;
  const completed = all.filter((t) => t.status === 'SUCCESS').length;
  const failed = all.filter((t) => t.status === 'FAILURE').length;
  return [
    { value: 'ALL', label: '全部', count: all.length },
    { value: 'RUNNING', label: '运行中', count: running },
    { value: 'SUCCESS', label: '已完成', count: completed },
    { value: 'FAILURE', label: '失败', count: failed },
  ];
});

const filteredTasks = computed(() => {
  if (taskFilter.value === 'ALL') return taskList.value;
  if (taskFilter.value === 'RUNNING') {
    return taskList.value.filter((t) => ACTIVE_STATUSES.has(String(t.status || '').toUpperCase()));
  }
  return taskList.value.filter((t) => t.status === taskFilter.value);
});

const filteredDocuments = computed(() => {
  const q = docSearchQuery.value.toLowerCase();
  return (docsInventory.documents || []).filter((doc) => {
    if (docSourceFilter.value !== 'ALL' && doc.source_type !== docSourceFilter.value) {
      return false;
    }
    if (!q) return true;
    const nameMatch = String(doc.filename || '').toLowerCase().includes(q);
    const catMatch = String(doc.category || '').toLowerCase().includes(q);
    const pathMatch = String(doc.relative_path || '').toLowerCase().includes(q);
    return nameMatch || catMatch || pathMatch;
  });
});

const showFeedback = (type, message) => {
  feedback.type = type;
  feedback.message = message;
};

const handleAuthFailure = (status, message) => {
  if (status === 401) {
    authStore.handleUnauthorized();
    router.replace({ path: '/login', query: { redirect: '/admin/tasks' } });
    return true;
  }
  if (status === 403) {
    authStore.setPermissionNotice(message || '权限不足：知识库运维与任务中心仅限系统管理员访问。');
    router.replace('/');
    return true;
  }
  return false;
};

const fetchKnowledgeStatus = async () => {
  const resp = await fetch('/api/v1/knowledge/status', {
    headers: authStore.getAuthHeaders(),
  });
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    if (handleAuthFailure(resp.status, json.message)) return;
    throw new Error(json.message || '读取知识库向量状态失败');
  }
  if (json.data) {
    Object.assign(kbStatus, json.data);
  }
};

const fetchDocumentsInventory = async () => {
  const resp = await fetch('/api/v1/knowledge/documents', {
    headers: authStore.getAuthHeaders(),
  });
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    if (handleAuthFailure(resp.status, json.message)) return;
    throw new Error(json.message || '读取知识库文档清单失败');
  }
  if (json.data) {
    docsInventory.documents = json.data.documents || [];
    docsInventory.total_count = json.data.total_count || 0;
    docsInventory.builtin_count = json.data.builtin_count || 0;
    docsInventory.uploaded_count = json.data.uploaded_count || 0;
    docsInventory.category_breakdown = json.data.category_breakdown || {};
  }
};

const fetchTaskList = async () => {
  const resp = await fetch('/api/v1/tasks?limit=30', {
    headers: authStore.getAuthHeaders(),
  });
  const json = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    if (handleAuthFailure(resp.status, json.message)) return;
    throw new Error(json.message || '读取异步任务台账失败');
  }
  if (json.data && Array.isArray(json.data.tasks)) {
    taskList.value = json.data.tasks;
    ensurePollingLoop();
  }
};

const refreshAllData = async () => {
  isRefreshing.value = true;
  try {
    await Promise.all([fetchKnowledgeStatus(), fetchDocumentsInventory(), fetchTaskList()]);
  } catch (err) {
    showFeedback('error', err.message || '加载知识库运行态信息失败');
  } finally {
    isRefreshing.value = false;
  }
};

const validateAndQueueFiles = (fileList) => {
  if (!fileList || fileList.length === 0) return;
  const rejected = [];
  const existingKeys = new Set(queuedFiles.value.map((q) => q.key));

  for (const file of fileList) {
    const dotIdx = file.name.lastIndexOf('.');
    const ext = dotIdx >= 0 ? file.name.slice(dotIdx).toLowerCase() : '';
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      rejected.push(`${file.name}（不支持格式 ${ext || '未知'}）`);
      continue;
    }
    if (file.size <= 0) {
      rejected.push(`${file.name}（文件内容为空）`);
      continue;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      rejected.push(`${file.name}（超过 20 MB 限制）`);
      continue;
    }
    const key = `${file.name}-${file.size}-${file.lastModified}`;
    if (!existingKeys.has(key)) {
      queuedFiles.value.push({
        key,
        file,
        ext: ext.replace(/^\./, ''),
      });
      existingKeys.add(key);
    }
  }

  if (rejected.length > 0) {
    showFeedback('error', `已拦截以下不合规文档：${rejected.join('；')}`);
  }
};

const triggerFilePicker = () => {
  fileInputRef.value?.click();
};

const handleFileSelected = (event) => {
  const files = Array.from(event.target?.files || []);
  validateAndQueueFiles(files);
  if (event.target) {
    event.target.value = '';
  }
};

const handleFileDrop = (event) => {
  isDragOver.value = false;
  const files = Array.from(event.dataTransfer?.files || []);
  validateAndQueueFiles(files);
};

const removeQueuedFile = (index) => {
  queuedFiles.value.splice(index, 1);
};

const upsertTaskInList = (taskPayload) => {
  if (!taskPayload || !taskPayload.task_id) return;
  const idx = taskList.value.findIndex((item) => item.task_id === taskPayload.task_id);
  if (idx >= 0) {
    taskList.value[idx] = { ...taskList.value[idx], ...taskPayload };
  } else {
    taskList.value.unshift(taskPayload);
  }
};

const pollSingleTaskStatus = async (taskId) => {
  try {
    const resp = await fetch(`/api/v1/tasks/${encodeURIComponent(taskId)}/status`, {
      headers: authStore.getAuthHeaders(),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      handleAuthFailure(resp.status, json.message);
      return null;
    }
    if (json.data) {
      upsertTaskInList(json.data);
      return json.data;
    }
  } catch {
    // 静默忽略单次轮询网络波动
  }
  return null;
};

const stopPollingLoop = () => {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const ensurePollingLoop = () => {
  if (activeTasks.value.length === 0) {
    stopPollingLoop();
    return;
  }
  if (pollTimer !== null) return;

  pollTimer = setInterval(async () => {
    const pendingList = activeTasks.value.map((t) => t.task_id);
    if (pendingList.length === 0) {
      stopPollingLoop();
      return;
    }
    let anyCompleted = false;
    const results = await Promise.all(pendingList.map((id) => pollSingleTaskStatus(id)));
    for (const item of results) {
      if (item && (item.status === 'SUCCESS' || item.status === 'FAILURE')) {
        anyCompleted = true;
      }
    }
    if (anyCompleted) {
      await Promise.all([fetchKnowledgeStatus(), fetchDocumentsInventory()]);
    }
    if (activeTasks.value.length === 0) {
      stopPollingLoop();
    }
  }, 1500);
};

const submitUploadQueue = async () => {
  if (queuedFiles.value.length === 0 || isUploading.value) return;
  isUploading.value = true;
  feedback.message = '';

  const pendingItems = [...queuedFiles.value];
  const isAsync = uploadMode.value === 'async';
  let successCount = 0;
  let fallbackUsed = false;
  const failures = [];

  try {
    for (const item of pendingItems) {
      const formData = new FormData();
      formData.append('file', item.file);
      if (selectedCategory.value && selectedCategory.value !== 'AUTO') {
        formData.append('category', selectedCategory.value);
      }
      formData.append('is_async', isAsync ? 'true' : 'false');

      const resp = await fetch('/api/v1/knowledge/upload', {
        method: 'POST',
        headers: authStore.getAuthHeaders(),
        body: formData,
      });
      const json = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        if (handleAuthFailure(resp.status, json.message)) return;
        failures.push(`${item.file.name}: ${json.message || '上传失败'}`);
        continue;
      }

      successCount += 1;
      const data = json.data || {};
      if (data.execution_mode === 'async_fallback') {
        fallbackUsed = true;
      }
      if (data.task_id) {
        await pollSingleTaskStatus(data.task_id);
      }
    }

    queuedFiles.value = [];
    await Promise.all([fetchKnowledgeStatus(), fetchDocumentsInventory(), fetchTaskList()]);
    ensurePollingLoop();

    if (failures.length > 0 && successCount === 0) {
      showFeedback('error', `文档上传失败：${failures.join('；')}`);
    } else if (failures.length > 0) {
      showFeedback('warning', `成功提交 ${successCount} 篇，部分失败：${failures.join('；')}`);
    } else if (isAsync) {
      showFeedback(
        fallbackUsed ? 'warning' : 'success',
        fallbackUsed
          ? `已提交 ${successCount} 篇异步解析任务（检测到本地未启动 Celery Worker，已自动切换后台队列无阻塞执行）`
          : `已成功将 ${successCount} 篇文档投递至 Celery 异步解析队列，下方正在实时追踪进度`
      );
    } else {
      showFeedback('success', `已完成 ${successCount} 篇文档的同步解析切片与 Qdrant / BM25 实时索引刷新`);
    }
  } catch (err) {
    showFeedback('error', err.message || '文档上传请求异常');
  } finally {
    isUploading.value = false;
  }
};

const executeKnowledgeSync = async (recreate) => {
  confirmSyncMode.value = '';
  isSyncing.value = true;
  activeSyncRecreate.value = recreate;
  feedback.message = '';

  try {
    const resp = await fetch(`/api/v1/knowledge/sync?recreate=${recreate ? 'true' : 'false'}`, {
      method: 'POST',
      headers: authStore.getAuthHeaders(),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      showFeedback('error', json.message || '知识库同步操作失败');
      return;
    }

    lastSyncReport.value = json.data || null;
    await Promise.all([fetchKnowledgeStatus(), fetchDocumentsInventory(), fetchTaskList()]);
    const pts = json.data?.qdrant_info?.points_count ?? kbStatus.points_count;
    showFeedback(
      'success',
      recreate
        ? `全量重建索引已完成，当前 Qdrant 集合共 ${pts} 条有效切片，HybridRetriever 已刷新`
        : `增量校验同步已完成，当前 Qdrant 集合共 ${pts} 条有效切片，HybridRetriever 已刷新`
    );
  } catch (err) {
    showFeedback('error', err.message || '知识库同步请求异常');
  } finally {
    isSyncing.value = false;
  }
};

const resolveFormatIcon = (ext) => {
  const norm = String(ext || '').toLowerCase();
  if (norm === 'xlsx' || norm === 'xls') return FileSpreadsheet;
  if (norm === 'md' || norm === 'txt' || norm === 'pdf') return FileText;
  return File;
};

const formatBytes = (bytes) => {
  const n = Number(bytes || 0);
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(2)} MB`;
};

const formatTime = (isoStr) => {
  if (!isoStr) return '--';
  try {
    return new Date(isoStr).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return String(isoStr);
  }
};

const formatExecutionMode = (mode) => {
  switch (mode) {
    case 'sync':
      return '同步快传';
    case 'sync_rebuild':
      return '全量重建';
    case 'celery_worker':
      return 'Celery Worker';
    case 'celery_eager':
      return 'Celery Eager';
    case 'async_fallback':
      return '后台异步队列';
    case 'builtin_kb':
      return '内置制度库';
    default:
      return mode || '标准入库';
  }
};

const mapTaskStatusToMark = (status) => {
  const s = String(status || 'PENDING').toUpperCase();
  if (s === 'SUCCESS' || s === 'COMPLETED') return 'success';
  if (s === 'FAILURE' || s === 'FAILED') return 'danger';
  if (s === 'PROGRESS' || s === 'STARTED' || s === 'PENDING' || s === 'RETRY') return 'running';
  return 'idle';
};

const progressBarColor = (status) => {
  const s = String(status || '').toUpperCase();
  if (s === 'SUCCESS') return 'bg-status-success';
  if (s === 'FAILURE') return 'bg-status-danger';
  return 'bg-action-primary';
};

const resolveTaskSteps = (task) => {
  if (Array.isArray(task.steps) && task.steps.length > 0) {
    return task.steps;
  }
  const done = task.status === 'SUCCESS';
  return [
    { key: 'QUEUED', label: '任务排队', status: done ? 'success' : 'running' },
    { key: 'PARSING', label: '文档解析', status: done ? 'success' : 'idle' },
    { key: 'CHUNKING', label: '语义切片', status: done ? 'success' : 'idle' },
    { key: 'INDEXING', label: '向量入库', status: done ? 'success' : 'idle' },
    { key: 'COMPLETED', label: '完成入库', status: done ? 'success' : 'idle' },
  ];
};

onMounted(() => {
  refreshAllData();
});

onBeforeUnmount(() => {
  stopPollingLoop();
});
</script>
