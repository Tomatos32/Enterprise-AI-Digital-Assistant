<template>
  <div
    class="viz-root h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-6 lg:p-8 transition-colors duration-200"
    :class="{ 'viz-dark': preferencesStore.isDark }"
  >
    <div class="max-w-7xl w-full mx-auto space-y-6 pb-12">
      <!-- Top Header & Unified Control Bar -->
      <header class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-start sm:items-center space-x-3">
          <div class="w-11 h-11 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-sm">
            <Activity class="w-5 h-5" />
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-base sm:text-lg font-bold text-text-main">系统监控与 SLA 看板</h1>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 inline-flex items-center space-x-1">
                <ShieldCheck class="w-3 h-3" />
                <span>管理员专属域</span>
              </span>
              <StatusMark
                :status="overallHealthMarkStatus"
                :label="overallHealthLabel"
              />
            </div>
            <p class="text-xs text-text-secondary mt-1">
              实时洞察核心服务健康度、首字响应延迟分布、业务工具调用审计与 P0~P4 企业工单 SLA 履约状况
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2.5">
          <div class="flex items-center space-x-2">
            <span class="text-[11px] font-medium text-text-muted">静默轮询</span>
            <RubberSegment
              v-model="pollingIntervalMs"
              :options="pollingOptions"
            />
          </div>

          <FuseButton
            variant="secondary"
            size="md"
            :loading="isManualRefreshing"
            @click="loadOverview(false)"
          >
            <span class="inline-flex items-center space-x-1.5">
              <RefreshCw
                v-if="!isManualRefreshing"
                class="w-3.5 h-3.5 text-brand-primary"
                :class="{ 'animate-spin': isSilentRefreshing }"
              />
              <span>{{ isManualRefreshing ? '刷新中...' : '手动刷新' }}</span>
            </span>
          </FuseButton>

          <router-link
            to="/"
            class="px-3 py-1.5 rounded-xl glass-panel hover:bg-slate-200/60 dark:hover:bg-slate-800 text-xs text-text-secondary hover:text-text-main border border-border-subtle inline-flex items-center space-x-1.5 transition-colors duration-150"
          >
            <MessageSquare class="w-3.5 h-3.5 text-brand-primary" />
            <span>返回工作台</span>
          </router-link>
        </div>
      </header>

      <!-- Sync Status & Error Banner -->
      <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] text-text-muted">
        <div class="flex items-center space-x-2">
          <Clock class="w-3.5 h-3.5" />
          <span>最近采样时间:</span>
          <span class="tabular-nums font-medium text-text-secondary">{{ formattedGeneratedAt }}</span>
          <span v-if="isSilentRefreshing" class="text-brand-primary font-medium">正在静默同步最新快照...</span>
        </div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>活跃推理引擎: <strong class="text-text-secondary">{{ llmEngineMeta.model || '-' }}</strong></span>
          <span>向量集合点位: <strong class="tabular-nums text-text-secondary">{{ formatInteger(qdrantMeta.points_count) }}</strong></span>
          <span>活跃入库任务: <strong class="tabular-nums text-text-secondary">{{ formatInteger(systemHealth.active_ingestion_tasks) }}</strong></span>
        </div>
      </div>

      <div
        v-if="errorMessage"
        class="p-3.5 rounded-2xl border bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-300 flex items-center justify-between gap-3 text-xs"
      >
        <div class="flex items-center space-x-2">
          <AlertCircle class="w-4 h-4 shrink-0" />
          <span>{{ errorMessage }}</span>
        </div>
        <button
          type="button"
          @click="errorMessage = ''"
          class="p-1 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 cursor-pointer"
          aria-label="关闭提示"
        >
          <X class="w-3.5 h-3.5" />
        </button>
      </div>

      <!-- Main Content Container (retains previous render at reduced opacity during silent refresh) -->
      <div
        class="space-y-6 transition-opacity duration-200"
        :class="{ 'opacity-70': isSilentRefreshing && hasLoadedOnce }"
      >
        <!-- Section 1: Component Health Strip -->
        <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          <div
            v-for="comp in componentHealthList"
            :key="comp.key"
            class="rounded-2xl glass-card border border-border-card p-4 flex items-start justify-between gap-3 shadow-sm"
          >
            <div class="min-w-0 space-y-1">
              <div class="flex items-center space-x-2">
                <component :is="resolveComponentIcon(comp.key)" class="w-4 h-4 text-text-secondary shrink-0" />
                <span class="text-xs font-semibold text-text-main truncate">{{ comp.name }}</span>
              </div>
              <div class="text-[11px] text-text-secondary truncate" :title="comp.detail">{{ comp.detail }}</div>
              <div class="text-[10px] text-text-muted">模式: {{ comp.mode }}</div>
            </div>
            <span
              class="px-2 py-0.5 rounded-lg text-[10px] font-semibold border inline-flex items-center space-x-1 shrink-0"
              :class="healthBadgeClass(comp.status)"
            >
              <CheckCircle2 v-if="comp.status === 'UP' || comp.status === 'READY'" class="w-3 h-3" />
              <AlertTriangle v-else class="w-3 h-3" />
              <span>{{ healthText(comp.status) }}</span>
            </span>
          </div>
        </section>

        <!-- Section 2: Core KPI Stat Tiles (Proportional display numbers) -->
        <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <!-- KPI 1: WebSocket & Chat Throughput -->
          <div class="rounded-3xl glass-card border border-border-card p-5 space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-text-secondary">实时 WebSocket 连接</span>
              <div class="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
                <Radio class="w-4 h-4" />
              </div>
            </div>
            <div class="flex items-baseline space-x-2">
              <span class="kpi-value text-3xl font-bold text-text-main tracking-tight">
                {{ formatInteger(telemetry.active_websocket_connections) }}
              </span>
              <span class="text-xs text-text-muted">在线通道</span>
            </div>
            <div class="text-[11px] text-text-secondary flex flex-wrap gap-x-3 gap-y-0.5">
              <span>有效会话 {{ formatInteger(business.chat.active_sessions) }}</span>
              <span>累计消息 {{ formatInteger(business.chat.total_messages) }}</span>
              <span>均值思考 {{ business.chat.avg_thinking_seconds }}s</span>
            </div>
          </div>

          <!-- KPI 2: Cumulative Token Consumption (Input vs Output) -->
          <div class="rounded-3xl glass-card border border-border-card p-5 space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-text-secondary">累计 Token 消耗</span>
              <div class="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                <Coins class="w-4 h-4" />
              </div>
            </div>
            <div class="flex items-baseline space-x-2" :title="`总计 ${formatInteger(telemetry.tokens.total_tokens)} tokens`">
              <span class="kpi-value text-3xl font-bold text-text-main tracking-tight">
                {{ formatCompactNumber(telemetry.tokens.total_tokens) }}
              </span>
              <span class="text-xs text-text-muted">Tokens</span>
            </div>
            <div class="space-y-1.5">
              <div class="flex items-center justify-between text-[11px] text-text-secondary">
                <span>输入 {{ formatCompactNumber(telemetry.tokens.input_tokens) }}</span>
                <span>输出 {{ formatCompactNumber(telemetry.tokens.output_tokens) }}</span>
              </div>
              <!-- Thin proportional segmented bar with 2px surface gap -->
              <div class="h-2 w-full rounded-full overflow-hidden flex bg-slate-200/70 dark:bg-slate-800/80">
                <div
                  v-if="tokenSplit.inputPct > 0"
                  class="h-full transition-all duration-300"
                  :class="tokenSplit.outputPct > 0 ? 'rounded-l-full' : 'rounded-full'"
                  :style="{ width: `${tokenSplit.inputPct}%`, backgroundColor: 'var(--viz-series-1)' }"
                ></div>
                <div
                  v-if="tokenSplit.inputPct > 0 && tokenSplit.outputPct > 0"
                  class="w-[2px] h-full shrink-0"
                  :style="{ backgroundColor: 'var(--viz-surface)' }"
                ></div>
                <div
                  v-if="tokenSplit.outputPct > 0"
                  class="h-full transition-all duration-300"
                  :class="tokenSplit.inputPct > 0 ? 'rounded-r-full' : 'rounded-full'"
                  :style="{ width: `${tokenSplit.outputPct}%`, backgroundColor: 'var(--viz-series-2)' }"
                ></div>
              </div>
            </div>
          </div>

          <!-- KPI 3: Prompt Cache Hit Rate -->
          <div class="rounded-3xl glass-card border border-border-card p-5 space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-text-secondary">提示词缓存命中率</span>
              <div class="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <Zap class="w-4 h-4" />
              </div>
            </div>
            <div class="flex items-baseline space-x-2">
              <span class="kpi-value text-3xl font-bold text-text-main tracking-tight">
                {{ telemetry.prompt_cache.total_lookups > 0 ? `${telemetry.prompt_cache.hit_rate_percent}%` : '0%' }}
              </span>
              <span class="text-xs text-text-muted">
                {{ telemetry.prompt_cache.total_lookups > 0 ? '命中效率' : '待触发查询' }}
              </span>
            </div>
            <div class="text-[11px] text-text-secondary">
              命中 {{ formatInteger(telemetry.prompt_cache.hits) }} 次 · 未命中 {{ formatInteger(telemetry.prompt_cache.misses) }} 次
            </div>
          </div>

          <!-- KPI 4: Approval Closure -->
          <div class="rounded-3xl glass-card border border-border-card p-5 space-y-2.5 shadow-sm">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-text-secondary">人机审批闭环率</span>
              <div class="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center">
                <ClipboardCheck class="w-4 h-4" />
              </div>
            </div>
            <div class="flex items-baseline space-x-2">
              <span class="kpi-value text-3xl font-bold text-text-main tracking-tight">
                {{ business.approvals.total_count > 0 ? `${business.approvals.closure_rate_percent}%` : '0%' }}
              </span>
              <span class="text-xs text-text-muted">
                待办 {{ formatInteger(business.approvals.pending_count) }} 项
              </span>
            </div>
            <div class="text-[11px] text-text-secondary">
              已批准 {{ formatInteger(business.approvals.approved_count) }} · 已驳回 {{ formatInteger(business.approvals.rejected_count) }}
            </div>
          </div>
        </section>

        <!-- Section 3: Interactive Charts Row (TTFT Distribution & Tool Invocations) -->
        <section class="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <!-- Chart A: TTFT Ordinal 5-Bucket Distribution (6 cols) -->
          <div class="lg:col-span-6 rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-4 shadow-md flex flex-col">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 class="text-sm font-bold text-text-main">首字响应延迟分布</h2>
                <p class="text-[11px] text-text-secondary mt-0.5">
                  非累积五档分桶样本 {{ formatInteger(telemetry.ttft.total_observations) }} 次 · 均值 {{ telemetry.ttft.avg_ms }} ms
                </p>
              </div>
              <div class="inline-flex p-0.5 rounded-xl bg-slate-200/70 dark:bg-slate-900/80 border border-border-subtle">
                <button
                  type="button"
                  @click="ttftViewMode = 'chart'"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer inline-flex items-center space-x-1"
                  :class="ttftViewMode === 'chart' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm' : 'text-text-secondary hover:text-text-main'"
                >
                  <BarChart3 class="w-3 h-3" />
                  <span>图表</span>
                </button>
                <button
                  type="button"
                  @click="ttftViewMode = 'table'"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer inline-flex items-center space-x-1"
                  :class="ttftViewMode === 'table' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm' : 'text-text-secondary hover:text-text-main'"
                >
                  <Table2 class="w-3 h-3" />
                  <span>数据表</span>
                </button>
              </div>
            </div>

            <!-- SVG Ordinal Column Chart -->
            <div v-if="ttftViewMode === 'chart'" class="relative flex-1 flex flex-col justify-between">
              <div class="relative w-full">
                <svg
                  viewBox="0 0 520 230"
                  class="w-full h-auto overflow-visible select-none"
                  role="img"
                  aria-label="首字响应延迟五档序数分布柱状图"
                >
                  <!-- Solid 1px hairline horizontal gridlines -->
                  <g v-for="tick in ttftYAxisTicks" :key="`ttft-grid-${tick.value}`">
                    <line
                      :x1="44"
                      :y1="tick.y"
                      :x2="504"
                      :y2="tick.y"
                      stroke="var(--viz-gridline)"
                      stroke-width="1"
                    />
                    <text
                      x="38"
                      :y="tick.y + 3.5"
                      text-anchor="end"
                      fill="var(--viz-ink-muted)"
                      class="text-[10px] tabular-svg-text"
                    >
                      {{ tick.label }}
                    </text>
                  </g>

                  <!-- Solid baseline -->
                  <line
                    x1="44"
                    y1="186"
                    x2="504"
                    y2="186"
                    stroke="var(--viz-axis)"
                    stroke-width="1"
                  />

                  <!-- 5 Ordinal Columns (<=24px wide, 4px rounded top, square baseline) -->
                  <g
                    v-for="(item, idx) in ttftChartBars"
                    :key="item.bucket"
                  >
                    <path
                      v-if="item.barHeight > 0"
                      :d="topRoundedBarPath(item.barX, item.barY, item.barWidth, item.barHeight, 4)"
                      :fill="item.color"
                      class="transition-opacity duration-150"
                      :class="{ 'opacity-45': hoveredTtftIdx !== null && hoveredTtftIdx !== idx }"
                    />
                    <!-- Selective direct label on cap when count > 0 -->
                    <text
                      v-if="item.count > 0"
                      :x="item.centerX"
                      :y="Math.max(14, item.barY - 6)"
                      text-anchor="middle"
                      fill="var(--viz-ink-primary)"
                      class="text-[11px] font-semibold tabular-svg-text"
                    >
                      {{ item.count }}
                    </text>
                    <!-- X-axis bucket label -->
                    <text
                      :x="item.centerX"
                      y="206"
                      text-anchor="middle"
                      fill="var(--viz-ink-secondary)"
                      class="text-[10.5px] tabular-svg-text"
                    >
                      {{ item.bucket }}
                    </text>
                    <!-- Focus / Hover indicator ring -->
                    <rect
                      v-if="hoveredTtftIdx === idx"
                      :x="item.barX - 4"
                      y="14"
                      :width="item.barWidth + 8"
                      height="176"
                      rx="6"
                      fill="none"
                      stroke="var(--viz-series-1)"
                      stroke-width="1.25"
                      stroke-opacity="0.45"
                    />
                    <!-- Generous keyboard & pointer hit target (>= 44px wide) -->
                    <rect
                      :x="item.hitX"
                      y="16"
                      :width="item.hitWidth"
                      height="176"
                      fill="transparent"
                      tabindex="0"
                      class="cursor-pointer focus:outline-none"
                      :aria-label="`${item.bucket}: ${item.count} 次 (${item.share_percent}%)`"
                      @mouseenter="hoveredTtftIdx = idx"
                      @mouseleave="hoveredTtftIdx = null"
                      @focus="hoveredTtftIdx = idx"
                      @blur="hoveredTtftIdx = null"
                    />
                  </g>
                </svg>

                <!-- Hover / Focus Tooltip -->
                <div
                  v-if="activeTtftItem"
                  class="mt-2 px-3 py-2 rounded-xl border border-border-card bg-bg-card/95 shadow-md flex items-center justify-between text-xs"
                >
                  <div class="flex items-center space-x-2">
                    <span
                      class="inline-block w-3 h-1 rounded-full"
                      :style="{ backgroundColor: activeTtftItem.color }"
                    ></span>
                    <span class="text-text-secondary">{{ activeTtftItem.bucket }}</span>
                  </div>
                  <div class="font-semibold text-text-main tabular-nums">
                    {{ activeTtftItem.count }} 次 ({{ activeTtftItem.share_percent }}%)
                  </div>
                </div>
                <div
                  v-else-if="telemetry.ttft.total_observations === 0"
                  class="mt-2 px-3 py-2 rounded-xl border border-dashed border-border-subtle text-[11px] text-text-muted text-center"
                >
                  当前暂无首字延迟样本；发起对话流后将自动记录五档耗时分布。
                </div>
                <div
                  v-else
                  class="mt-2 px-3 py-2 rounded-xl border border-border-subtle/60 text-[11px] text-text-muted flex items-center justify-between"
                >
                  <span>悬停或键盘聚焦柱条查看各档精确样本与占比</span>
                  <span class="tabular-nums">总观测 {{ telemetry.ttft.total_observations }} 次</span>
                </div>
              </div>
            </div>

            <!-- Table Twin View for TTFT -->
            <div v-else class="overflow-x-auto rounded-2xl border border-border-subtle">
              <table class="w-full text-left border-collapse text-xs">
                <thead>
                  <tr class="bg-slate-100/90 dark:bg-slate-900/90 text-[11px] text-text-secondary border-b border-border-subtle">
                    <th class="py-2.5 px-3 font-semibold">延迟区间</th>
                    <th class="py-2.5 px-3 font-semibold text-right">观测次数</th>
                    <th class="py-2.5 px-3 font-semibold text-right">占比</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/70">
                  <tr v-for="item in ttftChartBars" :key="`ttft-row-${item.bucket}`">
                    <td class="py-2.5 px-3 flex items-center space-x-2">
                      <span class="w-2.5 h-2.5 rounded-sm shrink-0" :style="{ backgroundColor: item.color }"></span>
                      <span class="font-medium text-text-main tabular-nums">{{ item.bucket }}</span>
                    </td>
                    <td class="py-2.5 px-3 text-right font-semibold text-text-main tabular-nums">{{ item.count }}</td>
                    <td class="py-2.5 px-3 text-right text-text-secondary tabular-nums">{{ item.share_percent }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Chart B: Tool Execution Statistics (6 cols) -->
          <div class="lg:col-span-6 rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-4 shadow-md flex flex-col">
            <div class="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 class="text-sm font-bold text-text-main">业务与检索工具调用分布</h2>
                <p class="text-[11px] text-text-secondary mt-0.5">
                  已注册工具 {{ telemetry.tools.registered_count }} 个 · 累计调用 {{ formatInteger(telemetry.tools.total_calls) }} 次 · 成功率
                  {{ telemetry.tools.total_calls > 0 ? `${telemetry.tools.success_rate_percent}%` : '暂无调用' }}
                </p>
              </div>
              <div class="inline-flex p-0.5 rounded-xl bg-slate-200/70 dark:bg-slate-900/80 border border-border-subtle">
                <button
                  type="button"
                  @click="toolsViewMode = 'chart'"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer inline-flex items-center space-x-1"
                  :class="toolsViewMode === 'chart' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm' : 'text-text-secondary hover:text-text-main'"
                >
                  <BarChart3 class="w-3 h-3" />
                  <span>图表</span>
                </button>
                <button
                  type="button"
                  @click="toolsViewMode = 'table'"
                  class="px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer inline-flex items-center space-x-1"
                  :class="toolsViewMode === 'table' ? 'bg-white dark:bg-slate-800 text-text-main shadow-sm' : 'text-text-secondary hover:text-text-main'"
                >
                  <Table2 class="w-3 h-3" />
                  <span>数据表</span>
                </button>
              </div>
            </div>

            <!-- Required Legend for 2-series Categorical Bar Chart -->
            <div class="flex items-center space-x-5 text-[11px] text-text-secondary">
              <div class="inline-flex items-center space-x-1.5">
                <span class="w-3 h-2.5 rounded-sm inline-block" style="background-color: var(--viz-series-1);"></span>
                <span>成功调用</span>
              </div>
              <div class="inline-flex items-center space-x-1.5">
                <span class="w-3 h-2.5 rounded-sm inline-block" style="background-color: var(--viz-series-2);"></span>
                <span>异常调用</span>
              </div>
            </div>

            <!-- Horizontal Stacked Bar SVG Chart -->
            <div v-if="toolsViewMode === 'chart'" class="flex-1 flex flex-col justify-between">
              <div
                v-if="toolChartRows.length === 0"
                class="flex-1 min-h-[180px] rounded-2xl border border-dashed border-border-subtle flex items-center justify-center text-xs text-text-muted px-4 text-center"
              >
                当前暂未注册或触发任何业务工具；智能体绑定工具后将在此展示调用分布。
              </div>
              <svg
                v-else
                :viewBox="`0 0 540 ${toolChartHeight}`"
                class="w-full h-auto overflow-visible select-none"
                role="img"
                aria-label="注册工具成功与异常调用水平柱状图"
              >
                <!-- Solid 1px hairline vertical gridlines -->
                <g v-for="tick in toolXAxisTicks" :key="`tool-grid-${tick.value}`">
                  <line
                    :x1="tick.x"
                    y1="8"
                    :x2="tick.x"
                    :y2="toolChartPlotBottom"
                    stroke="var(--viz-gridline)"
                    stroke-width="1"
                  />
                  <text
                    :x="tick.x"
                    :y="toolChartPlotBottom + 16"
                    text-anchor="middle"
                    fill="var(--viz-ink-muted)"
                    class="text-[10px] tabular-svg-text"
                  >
                    {{ tick.label }}
                  </text>
                </g>

                <!-- Left Y-axis baseline -->
                <line
                  x1="168"
                  y1="8"
                  x2="168"
                  :y2="toolChartPlotBottom"
                  stroke="var(--viz-axis)"
                  stroke-width="1"
                />

                <!-- Tool Horizontal Stacked Bars (<=24px height, 2px surface gap, 4px rounded right end) -->
                <g v-for="(row, idx) in toolChartRows" :key="row.tool_name">
                  <text
                    x="160"
                    :y="row.y + 13"
                    text-anchor="end"
                    fill="var(--viz-ink-secondary)"
                    class="text-[11px] font-medium"
                  >
                    {{ truncateLabel(row.tool_name, 24) }}
                  </text>

                  <!-- Subtle baseline track when 0 calls -->
                  <rect
                    v-if="row.total_count === 0"
                    x="168"
                    :y="row.y + 7"
                    width="8"
                    height="4"
                    rx="2"
                    fill="var(--viz-gridline)"
                  />

                  <!-- Success Segment -->
                  <path
                    v-if="row.successWidth > 0"
                    :d="rightRoundedOrFlatBarPath(168, row.y, row.successWidth, 18, row.errorWidth > 0 ? 0 : 4)"
                    fill="var(--viz-series-1)"
                    class="transition-opacity duration-150"
                    :class="{ 'opacity-45': hoveredToolIdx !== null && hoveredToolIdx !== idx }"
                  />

                  <!-- Error Segment (separated by 2px surface gap if both exist) -->
                  <path
                    v-if="row.errorWidth > 0"
                    :d="rightRoundedOrFlatBarPath(row.errorX, row.y, row.errorWidth, 18, 4)"
                    fill="var(--viz-series-2)"
                    class="transition-opacity duration-150"
                    :class="{ 'opacity-45': hoveredToolIdx !== null && hoveredToolIdx !== idx }"
                  />

                  <!-- Direct label at bar tip when total > 0 -->
                  <text
                    v-if="row.total_count > 0"
                    :x="row.labelX"
                    :y="row.y + 13"
                    text-anchor="start"
                    fill="var(--viz-ink-primary)"
                    class="text-[11px] font-semibold tabular-svg-text"
                  >
                    {{ row.total_count }}
                  </text>

                  <!-- Focus / Hover row highlight -->
                  <rect
                    v-if="hoveredToolIdx === idx"
                    x="4"
                    :y="row.y - 4"
                    width="532"
                    height="26"
                    rx="6"
                    fill="none"
                    stroke="var(--viz-series-1)"
                    stroke-width="1"
                    stroke-opacity="0.35"
                  />

                  <!-- Full-row keyboard & pointer hit target -->
                  <rect
                    x="0"
                    :y="row.y - 5"
                    width="540"
                    height="28"
                    fill="transparent"
                    tabindex="0"
                    class="cursor-pointer focus:outline-none"
                    :aria-label="`${row.tool_name}: 成功 ${row.success_count} 次, 异常 ${row.error_count} 次`"
                    @mouseenter="hoveredToolIdx = idx"
                    @mouseleave="hoveredToolIdx = null"
                    @focus="hoveredToolIdx = idx"
                    @blur="hoveredToolIdx = null"
                  />
                </g>
              </svg>

              <!-- Interactive Hover / Focus Readout -->
              <div
                v-if="activeToolRow"
                class="mt-2 px-3 py-2 rounded-xl border border-border-card bg-bg-card/95 shadow-md flex flex-wrap items-center justify-between gap-2 text-xs"
              >
                <div class="min-w-0">
                  <span class="font-semibold text-text-main">{{ activeToolRow.tool_name }}</span>
                  <span class="text-text-muted ml-2 text-[11px]">{{ activeToolRow.description }}</span>
                </div>
                <div class="flex items-center space-x-3 tabular-nums font-medium">
                  <span class="text-text-main">成功 {{ activeToolRow.success_count }}</span>
                  <span class="text-text-secondary">异常 {{ activeToolRow.error_count }}</span>
                  <span class="text-text-muted">均耗 {{ activeToolRow.avg_latency_ms }} ms</span>
                </div>
              </div>
              <div
                v-else
                class="mt-2 px-3 py-2 rounded-xl border border-border-subtle/60 text-[11px] text-text-muted flex items-center justify-between"
              >
                <span>悬停或键盘聚焦工具行查看成功/异常次数与平均延迟</span>
                <span class="tabular-nums">共 {{ toolChartRows.length }} 项工具</span>
              </div>
            </div>

            <!-- Table Twin View for Tools -->
            <div v-else class="overflow-x-auto rounded-2xl border border-border-subtle">
              <table class="w-full text-left border-collapse text-xs">
                <thead>
                  <tr class="bg-slate-100/90 dark:bg-slate-900/90 text-[11px] text-text-secondary border-b border-border-subtle">
                    <th class="py-2.5 px-3 font-semibold">工具名称</th>
                    <th class="py-2.5 px-3 font-semibold text-right">成功</th>
                    <th class="py-2.5 px-3 font-semibold text-right">异常</th>
                    <th class="py-2.5 px-3 font-semibold text-right">成功率</th>
                    <th class="py-2.5 px-3 font-semibold text-right">平均耗时</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/70">
                  <tr v-if="!telemetry.tools.by_tool || telemetry.tools.by_tool.length === 0">
                    <td colspan="5" class="py-8 text-center text-text-muted">
                      当前暂未注册或触发任何业务工具。
                    </td>
                  </tr>
                  <tr v-for="row in telemetry.tools.by_tool" :key="`tool-tbl-${row.tool_name}`">
                    <td class="py-2.5 px-3">
                      <div class="font-semibold text-text-main">{{ row.tool_name }}</div>
                      <div class="text-[10px] text-text-muted truncate max-w-[220px]" :title="row.description">{{ row.description }}</div>
                    </td>
                    <td class="py-2.5 px-3 text-right tabular-nums text-text-main">{{ row.success_count }}</td>
                    <td class="py-2.5 px-3 text-right tabular-nums text-text-secondary">{{ row.error_count }}</td>
                    <td class="py-2.5 px-3 text-right tabular-nums font-medium text-text-main">
                      {{ row.total_count > 0 ? `${row.success_rate_percent}%` : '—' }}
                    </td>
                    <td class="py-2.5 px-3 text-right tabular-nums text-text-secondary">
                      {{ row.total_count > 0 ? `${row.avg_latency_ms} ms` : '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- Section 4: Recent Tool Execution Audit Stream -->
        <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-4 shadow-md">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div class="flex items-center space-x-2.5">
              <div class="w-8 h-8 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
                <Wrench class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-bold text-text-main">近期工具调用安全审计流水</h2>
                <p class="text-[11px] text-text-muted">全链路参数脱敏记录，实时追踪工具响应延迟与异常诊断摘要</p>
              </div>
            </div>

            <div class="flex items-center space-x-1.5 text-[11px]">
              <button
                v-for="tab in auditStatusFilters"
                :key="tab.value"
                type="button"
                @click="auditFilter = tab.value"
                class="px-2.5 py-1 rounded-xl border font-medium transition-colors cursor-pointer"
                :class="
                  auditFilter === tab.value
                    ? 'bg-brand-primary text-white border-brand-primary'
                    : 'bg-slate-100/80 dark:bg-slate-900/60 text-text-secondary border-border-subtle hover:text-text-main'
                "
              >
                {{ tab.label }}
              </button>
            </div>
          </div>

          <div class="overflow-x-auto rounded-2xl border border-border-subtle">
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="bg-slate-100/90 dark:bg-slate-900/90 text-[11px] text-text-secondary border-b border-border-subtle">
                  <th class="py-2.5 px-3.5 font-semibold">审计流水号</th>
                  <th class="py-2.5 px-3 font-semibold">工具名称</th>
                  <th class="py-2.5 px-3 font-semibold">执行状态</th>
                  <th class="py-2.5 px-3 font-semibold text-right">耗时 (ms)</th>
                  <th class="py-2.5 px-3 font-semibold">脱敏执行摘要</th>
                  <th class="py-2.5 px-3 font-semibold text-right">调用时间</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/70">
                <tr v-if="filteredToolAudits.length === 0">
                  <td colspan="6" class="py-8 text-center text-text-muted">
                    暂无匹配的近期工具调用审计记录；智能体调度业务或检索工具后将自动记录脱敏流水。
                  </td>
                </tr>
                <tr
                  v-for="audit in filteredToolAudits"
                  :key="audit.audit_id"
                  class="hover:bg-slate-100/60 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <td class="py-2.5 px-3.5 font-medium text-text-secondary tabular-nums whitespace-nowrap">{{ audit.audit_id }}</td>
                  <td class="py-2.5 px-3 font-semibold text-text-main whitespace-nowrap">{{ audit.tool_name }}</td>
                  <td class="py-2.5 px-3 whitespace-nowrap">
                    <span
                      class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold border"
                      :class="
                        audit.status === 'success'
                          ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                          : 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30'
                      "
                    >
                      <CheckCircle2 v-if="audit.status === 'success'" class="w-3 h-3" />
                      <AlertCircle v-else class="w-3 h-3" />
                      <span>{{ audit.status === 'success' ? '调用成功' : '调用异常' }}</span>
                    </span>
                  </td>
                  <td class="py-2.5 px-3 text-right tabular-nums text-text-main whitespace-nowrap">{{ audit.duration_ms }}</td>
                  <td class="py-2.5 px-3 text-text-secondary max-w-[340px] truncate" :title="audit.summary">
                    {{ audit.summary || '已完成执行' }}
                  </td>
                  <td class="py-2.5 px-3 text-right tabular-nums text-text-muted whitespace-nowrap">
                    {{ formatIsoTime(audit.timestamp) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <!-- Section 5: Enterprise P0-P4 SLA Compliance & Recent Tickets -->
        <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-5 shadow-md">
          <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div class="flex items-center space-x-2.5">
              <div class="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
                <ShieldAlert class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-bold text-text-main">企业工单与 P0~P4 SLA 履约追踪</h2>
                <p class="text-[11px] text-text-muted">
                  依据企业运维服务级别协议核验响应/解决时效，实时标识履约与超期风险工单
                </p>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-2 text-xs">
              <span class="px-2.5 py-1 rounded-xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle text-text-secondary tabular-nums">
                总工单 <strong class="text-text-main">{{ business.sla.total_tickets }}</strong>
              </span>
              <span class="px-2.5 py-1 rounded-xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle text-text-secondary tabular-nums">
                处理中 <strong class="text-text-main">{{ business.sla.open_tickets }}</strong>
              </span>
              <span class="px-2.5 py-1 rounded-xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle text-text-secondary tabular-nums">
                已闭环 <strong class="text-text-main">{{ business.sla.closed_tickets }}</strong>
              </span>
              <span
                class="px-2.5 py-1 rounded-xl border inline-flex items-center space-x-1 font-semibold tabular-nums"
                :class="
                  business.sla.breached_tickets > 0
                    ? 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30'
                    : 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                "
              >
                <AlertTriangle v-if="business.sla.breached_tickets > 0" class="w-3.5 h-3.5" />
                <CheckCircle2 v-else class="w-3.5 h-3.5" />
                <span>整体 SLA 履约率 {{ business.sla.overall_compliance_percent }}%</span>
              </span>
            </div>
          </div>

          <!-- P0-P4 SLA Tiers Table -->
          <div class="overflow-x-auto rounded-2xl border border-border-subtle">
            <table class="w-full text-left border-collapse text-xs">
              <thead>
                <tr class="bg-slate-100/90 dark:bg-slate-900/90 text-[11px] text-text-secondary border-b border-border-subtle">
                  <th class="py-2.5 px-3.5 font-semibold">故障级别</th>
                  <th class="py-2.5 px-3 font-semibold">响应 SLA</th>
                  <th class="py-2.5 px-3 font-semibold">解决 SLA</th>
                  <th class="py-2.5 px-3 font-semibold text-right">工单总量</th>
                  <th class="py-2.5 px-3 font-semibold text-right">待办 / 闭环 / 超期</th>
                  <th class="py-2.5 px-3 font-semibold">SLA 履约率</th>
                  <th class="py-2.5 px-3 font-semibold">默认处置策略</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border-subtle/70">
                <tr
                  v-for="tier in business.sla.tiers"
                  :key="tier.priority"
                  class="hover:bg-slate-100/60 dark:hover:bg-slate-900/50 transition-colors"
                >
                  <td class="py-2.5 px-3.5 whitespace-nowrap">
                    <span
                      class="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-lg text-[11px] font-semibold border"
                      :class="priorityBadgeClass(tier.priority)"
                    >
                      <Flame v-if="tier.priority === 'P0'" class="w-3 h-3" />
                      <AlertTriangle v-else-if="tier.priority === 'P1'" class="w-3 h-3" />
                      <ShieldCheck v-else class="w-3 h-3" />
                      <span>{{ tier.priority }} · {{ tier.level_label }}</span>
                    </span>
                  </td>
                  <td class="py-2.5 px-3 whitespace-nowrap tabular-nums text-text-main">{{ tier.response_sla }}</td>
                  <td class="py-2.5 px-3 whitespace-nowrap tabular-nums text-text-main">{{ tier.resolution_sla }}</td>
                  <td class="py-2.5 px-3 text-right font-semibold tabular-nums text-text-main">{{ tier.total_count }}</td>
                  <td class="py-2.5 px-3 text-right tabular-nums text-text-secondary whitespace-nowrap">
                    {{ tier.open_count }} / {{ tier.closed_count }} /
                    <span :class="tier.breached_count > 0 ? 'text-rose-600 dark:text-rose-400 font-semibold' : ''">
                      {{ tier.breached_count }}
                    </span>
                  </td>
                  <td class="py-2.5 px-3 min-w-[150px]">
                    <div v-if="tier.has_tickets" class="flex items-center space-x-2">
                      <div
                        class="flex-1 h-2 rounded-full overflow-hidden"
                        :style="{ backgroundColor: slaMeterTrackColor(tier.compliance_rate_percent) }"
                      >
                        <div
                          class="h-full rounded-full transition-all duration-300"
                          :style="{
                            width: `${tier.compliance_rate_percent}%`,
                            backgroundColor: slaMeterFillColor(tier.compliance_rate_percent),
                          }"
                        ></div>
                      </div>
                      <span class="tabular-nums font-semibold text-text-main w-11 text-right">
                        {{ tier.compliance_rate_percent }}%
                      </span>
                    </div>
                    <span v-else class="text-[11px] text-text-muted">暂无工单</span>
                  </td>
                  <td class="py-2.5 px-3 text-text-secondary">{{ tier.action_policy }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Recent Tickets Ledger -->
          <div class="space-y-2.5">
            <div class="flex items-center justify-between">
              <h3 class="text-xs font-bold text-text-main">近期企业服务工单台账</h3>
              <span class="text-[11px] text-text-muted tabular-nums">展示最近 {{ business.sla.recent_tickets.length }} 条</span>
            </div>

            <div class="overflow-x-auto rounded-2xl border border-border-subtle">
              <table class="w-full text-left border-collapse text-xs">
                <thead>
                  <tr class="bg-slate-100/90 dark:bg-slate-900/90 text-[11px] text-text-secondary border-b border-border-subtle">
                    <th class="py-2.5 px-3.5 font-semibold">工单编号</th>
                    <th class="py-2.5 px-3 font-semibold">级别</th>
                    <th class="py-2.5 px-3 font-semibold">工单标题</th>
                    <th class="py-2.5 px-3 font-semibold">受理部门</th>
                    <th class="py-2.5 px-3 font-semibold">SLA 状态</th>
                    <th class="py-2.5 px-3 font-semibold">承诺时效</th>
                    <th class="py-2.5 px-3 font-semibold text-right">创建时间</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border-subtle/70">
                  <tr v-if="business.sla.recent_tickets.length === 0">
                    <td colspan="7" class="py-8 text-center text-text-muted">
                      当前数据库暂无服务工单记录；通过对话发起工单申报后将在此实时跟踪 SLA 时效。
                    </td>
                  </tr>
                  <tr
                    v-for="ticket in business.sla.recent_tickets"
                    :key="ticket.ticket_id"
                    class="hover:bg-slate-100/60 dark:hover:bg-slate-900/50 transition-colors"
                  >
                    <td class="py-2.5 px-3.5 font-medium text-text-secondary tabular-nums whitespace-nowrap">{{ ticket.ticket_id }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <span
                        class="px-2 py-0.5 rounded-lg text-[10px] font-semibold border"
                        :class="priorityBadgeClass(ticket.priority)"
                      >
                        {{ ticket.priority }}
                      </span>
                    </td>
                    <td class="py-2.5 px-3 font-medium text-text-main max-w-[260px] truncate" :title="ticket.title">
                      {{ ticket.title }}
                    </td>
                    <td class="py-2.5 px-3 text-text-secondary whitespace-nowrap">{{ ticket.department }}</td>
                    <td class="py-2.5 px-3 whitespace-nowrap">
                      <span
                        class="inline-flex items-center space-x-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold border"
                        :class="ticketSlaBadgeClass(ticket.sla_state)"
                      >
                        <CheckCircle2 v-if="ticket.sla_state === '已闭环'" class="w-3 h-3" />
                        <Clock v-else-if="ticket.sla_state === '履约中'" class="w-3 h-3" />
                        <AlertCircle v-else class="w-3 h-3" />
                        <span>{{ ticket.sla_state }}</span>
                      </span>
                    </td>
                    <td class="py-2.5 px-3 text-text-secondary tabular-nums whitespace-nowrap">
                      {{ ticket.response_sla }} / {{ ticket.resolution_sla }}
                    </td>
                    <td class="py-2.5 px-3 text-right tabular-nums text-text-muted whitespace-nowrap">
                      {{ formatIsoTime(ticket.created_at) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import {
  Activity,
  ShieldCheck,
  RefreshCw,
  MessageSquare,
  Clock,
  AlertCircle,
  X,
  Database,
  Server,
  Layers,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Coins,
  Zap,
  ClipboardCheck,
  BarChart3,
  Table2,
  Wrench,
  ShieldAlert,
  Flame,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import { usePreferencesStore } from '../stores/preferencesStore';
import FuseButton from '../components/ui/FuseButton.vue';
import RubberSegment from '../components/ui/RubberSegment.vue';
import StatusMark from '../components/ui/StatusMark.vue';

const router = useRouter();
const authStore = useAuthStore();
const preferencesStore = usePreferencesStore();

// Validated Dataviz Ordinal Blue Ramps (light #ffffff & dark #0f172a)
const TTFT_ORDINAL_LIGHT = ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#0d366b'];
const TTFT_ORDINAL_DARK = ['#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4'];

const pollingOptions = [
  { value: 0, label: '关闭' },
  { value: 15000, label: '15s' },
  { value: 30000, label: '30s' },
];

const auditStatusFilters = [
  { value: 'ALL', label: '全部流水' },
  { value: 'success', label: '仅成功' },
  { value: 'error', label: '仅异常' },
];

const pollingIntervalMs = ref(0);
const isManualRefreshing = ref(false);
const isSilentRefreshing = ref(false);
const hasLoadedOnce = ref(false);
const errorMessage = ref('');

const ttftViewMode = ref('chart');
const toolsViewMode = ref('chart');
const auditFilter = ref('ALL');
const hoveredTtftIdx = ref(null);
const hoveredToolIdx = ref(null);

let pollTimer = null;
let activeAbortController = null;
let isUnmounted = false;

const overview = reactive({
  generated_at: '',
  system_health: {
    overall_status: 'HEALTHY',
    components: [],
    llm_engine: {
      provider: '',
      model: '',
      active_engine: '',
      thinking: false,
      has_api_key: false,
      api_key_masked: '',
    },
    qdrant: {
      status: 'healthy',
      client_mode: 'local_storage',
      points_count: 0,
      vector_size: 1024,
    },
    active_ingestion_tasks: 0,
  },
  telemetry: {
    active_websocket_connections: 0,
    celery_queue_depth: 0,
    tokens: {
      input_tokens: 0,
      output_tokens: 0,
      total_tokens: 0,
      by_model: [],
    },
    prompt_cache: {
      hits: 0,
      misses: 0,
      total_lookups: 0,
      hit_rate_percent: 0,
    },
    ttft: {
      total_observations: 0,
      avg_ms: 0,
      buckets: [
        { bucket: '<= 100ms', le_key: '0.1', count: 0, share_percent: 0 },
        { bucket: '100ms - 250ms', le_key: '0.25', count: 0, share_percent: 0 },
        { bucket: '250ms - 500ms', le_key: '0.5', count: 0, share_percent: 0 },
        { bucket: '500ms - 1.5s', le_key: '1.5', count: 0, share_percent: 0 },
        { bucket: '> 1.5s', le_key: '+Inf', count: 0, share_percent: 0 },
      ],
    },
    tools: {
      registered_count: 0,
      total_calls: 0,
      success_calls: 0,
      error_calls: 0,
      success_rate_percent: 0,
      by_tool: [],
      recent_audits: [],
    },
  },
  business: {
    chat: {
      active_sessions: 0,
      total_sessions: 0,
      total_messages: 0,
      user_messages: 0,
      assistant_messages: 0,
      avg_thinking_seconds: 0,
    },
    approvals: {
      pending_count: 0,
      approved_count: 0,
      rejected_count: 0,
      closed_count: 0,
      total_count: 0,
      closure_rate_percent: 0,
    },
    sla: {
      total_tickets: 0,
      open_tickets: 0,
      closed_tickets: 0,
      breached_tickets: 0,
      overall_compliance_percent: 100,
      tiers: [],
      recent_tickets: [],
    },
  },
});

const systemHealth = computed(() => overview.system_health);
const telemetry = computed(() => overview.telemetry);
const business = computed(() => overview.business);
const componentHealthList = computed(() => systemHealth.value.components || []);
const llmEngineMeta = computed(() => systemHealth.value.llm_engine || {});
const qdrantMeta = computed(() => systemHealth.value.qdrant || {});

const overallHealthMarkStatus = computed(() => {
  if (isManualRefreshing.value || isSilentRefreshing.value) return 'running';
  return systemHealth.value.overall_status === 'HEALTHY' ? 'success' : 'warning';
});

const overallHealthLabel = computed(() => {
  return systemHealth.value.overall_status === 'HEALTHY' ? '全组件运行健康' : '部分组件降级容灾';
});

const formattedGeneratedAt = computed(() => {
  if (!overview.generated_at) return '等待采集';
  return formatIsoTime(overview.generated_at);
});

const tokenSplit = computed(() => {
  const inp = Number(telemetry.value.tokens.input_tokens || 0);
  const out = Number(telemetry.value.tokens.output_tokens || 0);
  const total = inp + out;
  if (total <= 0) {
    return { inputPct: 0, outputPct: 0 };
  }
  if (inp > 0 && out === 0) {
    return { inputPct: 100, outputPct: 0 };
  }
  if (out > 0 && inp === 0) {
    return { inputPct: 0, outputPct: 100 };
  }
  const inputPct = Math.min(99, Math.max(1, Math.round((inp / total) * 100)));
  return { inputPct, outputPct: 100 - inputPct };
});

// TTFT SVG Chart Geometry (columns <= 24px wide, 4px rounded top)
const ttftMaxCount = computed(() => {
  const counts = (telemetry.value.ttft.buckets || []).map((b) => Number(b.count || 0));
  const rawMax = Math.max(4, ...counts);
  return Math.ceil(rawMax / 4) * 4;
});

const ttftYAxisTicks = computed(() => {
  const maxVal = ttftMaxCount.value;
  const plotTop = 20;
  const plotBottom = 186;
  const steps = 4;
  const ticks = [];
  for (let i = 0; i <= steps; i += 1) {
    const value = Math.round((maxVal / steps) * i);
    const y = plotBottom - ((plotBottom - plotTop) * i) / steps;
    ticks.push({ value, label: formatCompactNumber(value), y });
  }
  return ticks;
});

const ttftChartBars = computed(() => {
  const buckets = telemetry.value.ttft.buckets || [];
  const palette = preferencesStore.isDark ? TTFT_ORDINAL_DARK : TTFT_ORDINAL_LIGHT;
  const plotLeft = 48;
  const plotWidth = 452;
  const plotTop = 20;
  const plotBottom = 186;
  const plotHeight = plotBottom - plotTop;
  const maxVal = ttftMaxCount.value;
  const count = Math.max(1, buckets.length);
  const slotWidth = plotWidth / count;
  const barWidth = 24;

  return buckets.map((b, idx) => {
    const val = Number(b.count || 0);
    const ratio = maxVal > 0 ? val / maxVal : 0;
    const barHeight = val > 0 ? Math.max(4, Math.round(ratio * plotHeight)) : 0;
    const centerX = plotLeft + slotWidth * idx + slotWidth / 2;
    return {
      ...b,
      count: val,
      color: palette[idx % palette.length],
      barWidth,
      barX: centerX - barWidth / 2,
      barY: plotBottom - barHeight,
      barHeight,
      centerX,
      hitX: plotLeft + slotWidth * idx,
      hitWidth: slotWidth,
    };
  });
});

const activeTtftItem = computed(() => {
  if (hoveredTtftIdx.value === null) return null;
  return ttftChartBars.value[hoveredTtftIdx.value] || null;
});

// Tool Invocation Horizontal Stacked Bar Chart Geometry
const toolMaxCount = computed(() => {
  const totals = (telemetry.value.tools.by_tool || []).map((t) => Number(t.total_count || 0));
  const rawMax = Math.max(4, ...totals);
  return Math.ceil(rawMax / 4) * 4;
});

const toolChartRows = computed(() => {
  const tools = telemetry.value.tools.by_tool || [];
  const maxVal = toolMaxCount.value;
  const plotLeft = 168;
  const maxBarSpace = 328;
  const rowGap = 32;
  const topOffset = 14;

  return tools.map((t, idx) => {
    const succ = Number(t.success_count || 0);
    const err = Number(t.error_count || 0);
    const total = succ + err;
    const y = topOffset + idx * rowGap;
    const hasBoth = succ > 0 && err > 0;
    const gapPx = hasBoth ? 2 : 0;

    const totalPx = maxVal > 0 && total > 0 ? Math.max(6, Math.round((total / maxVal) * maxBarSpace)) : 0;
    let successWidth = total > 0 ? Math.round((succ / total) * (totalPx - gapPx)) : 0;
    let errorWidth = total > 0 ? Math.max(0, totalPx - gapPx - successWidth) : 0;
    if (succ > 0 && successWidth < 4) successWidth = 4;
    if (err > 0 && errorWidth < 4) errorWidth = 4;

    const errorX = plotLeft + successWidth + gapPx;
    const endX = plotLeft + successWidth + (err > 0 ? gapPx + errorWidth : 0);

    return {
      ...t,
      success_count: succ,
      error_count: err,
      total_count: total,
      y,
      successWidth,
      errorWidth,
      errorX,
      labelX: endX + 8,
    };
  });
});

const toolChartPlotBottom = computed(() => {
  const rows = Math.max(1, toolChartRows.value.length);
  return 14 + rows * 32 + 4;
});

const toolChartHeight = computed(() => toolChartPlotBottom.value + 28);

const toolXAxisTicks = computed(() => {
  const maxVal = toolMaxCount.value;
  const plotLeft = 168;
  const maxBarSpace = 328;
  const steps = 4;
  const ticks = [];
  for (let i = 0; i <= steps; i += 1) {
    const val = Math.round((maxVal / steps) * i);
    const x = plotLeft + (maxBarSpace * i) / steps;
    ticks.push({ value: val, label: formatCompactNumber(val), x });
  }
  return ticks;
});

const activeToolRow = computed(() => {
  if (hoveredToolIdx.value === null) return null;
  return toolChartRows.value[hoveredToolIdx.value] || null;
});

const filteredToolAudits = computed(() => {
  const audits = telemetry.value.tools.recent_audits || [];
  if (auditFilter.value === 'ALL') return audits;
  return audits.filter((a) => a.status === auditFilter.value);
});

const formatInteger = (val) => {
  return Number(val || 0).toLocaleString();
};

const formatCompactNumber = (val) => {
  const n = Number(val || 0);
  if (n >= 1000000) return `${(n / 1000000).toFixed(1)}M`;
  if (n >= 10000) return `${(n / 1000).toFixed(1)}K`;
  return n.toLocaleString();
};

const formatIsoTime = (iso) => {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return d.toLocaleString('zh-CN', {
      hour12: false,
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return iso;
  }
};

const truncateLabel = (text, maxLen) => {
  const str = String(text || '');
  if (str.length <= maxLen) return str;
  return `${str.slice(0, maxLen - 1)}…`;
};

const topRoundedBarPath = (x, y, w, h, r) => {
  if (h <= 0 || w <= 0) return '';
  const radius = Math.min(r, w / 2, h);
  const bottom = y + h;
  return [
    `M ${x} ${bottom}`,
    `L ${x} ${y + radius}`,
    `Q ${x} ${y} ${x + radius} ${y}`,
    `L ${x + w - radius} ${y}`,
    `Q ${x + w} ${y} ${x + w} ${y + radius}`,
    `L ${x + w} ${bottom}`,
    'Z',
  ].join(' ');
};

const rightRoundedOrFlatBarPath = (x, y, w, h, r) => {
  if (w <= 0 || h <= 0) return '';
  const radius = Math.min(r, w / 2, h / 2);
  if (radius <= 0) {
    return `M ${x} ${y} H ${x + w} V ${y + h} H ${x} Z`;
  }
  return [
    `M ${x} ${y}`,
    `L ${x + w - radius} ${y}`,
    `Q ${x + w} ${y} ${x + w} ${y + radius}`,
    `L ${x + w} ${y + h - radius}`,
    `Q ${x + w} ${y + h} ${x + w - radius} ${y + h}`,
    `L ${x} ${y + h}`,
    'Z',
  ].join(' ');
};

const resolveComponentIcon = (key) => {
  if (key === 'database') return Database;
  if (key === 'redis') return Server;
  if (key === 'qdrant') return Layers;
  return Cpu;
};

const healthBadgeClass = (status) => {
  if (status === 'UP' || status === 'READY') {
    return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30';
  }
  return 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30';
};

const healthText = (status) => {
  if (status === 'UP') return '在线';
  if (status === 'READY') return '就绪';
  return '降级容灾';
};

const priorityBadgeClass = (priority) => {
  if (priority === 'P0') return 'bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30';
  if (priority === 'P1') return 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30';
  if (priority === 'P2') return 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30';
  return 'bg-slate-200/70 dark:bg-slate-800 text-text-secondary border-border-subtle';
};

const slaMeterFillColor = (rate) => {
  if (rate >= 95) return '#0ca30c';
  if (rate >= 80) return '#fab219';
  return '#d03b3b';
};

const slaMeterTrackColor = (rate) => {
  if (rate >= 95) return 'rgba(12, 163, 12, 0.16)';
  if (rate >= 80) return 'rgba(250, 178, 25, 0.20)';
  return 'rgba(208, 59, 59, 0.18)';
};

const ticketSlaBadgeClass = (slaState) => {
  if (slaState === '已闭环') return 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30';
  if (slaState === '履约中') return 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30';
  return 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30';
};

const handleAuthFailure = (status, message) => {
  if (status === 401) {
    authStore.handleUnauthorized();
    router.replace({ path: '/login', query: { redirect: '/admin/monitoring' } });
    return true;
  }
  if (status === 403) {
    authStore.setPermissionNotice(message || '权限不足：系统监控与 SLA 看板仅限系统管理员访问。');
    router.replace('/');
    return true;
  }
  return false;
};

const loadOverview = async (silent = false) => {
  if (isUnmounted) return;
  if (silent) {
    if (isSilentRefreshing.value || isManualRefreshing.value) return;
    isSilentRefreshing.value = true;
  } else {
    isManualRefreshing.value = true;
    errorMessage.value = '';
  }

  if (activeAbortController) {
    activeAbortController.abort();
    activeAbortController = null;
  }
  const controller = new AbortController();
  activeAbortController = controller;

  try {
    const resp = await fetch('/api/v1/admin/monitoring/overview', {
      headers: authStore.getAuthHeaders(),
      signal: controller.signal,
    });
    const json = await resp.json().catch(() => ({}));
    if (isUnmounted || controller.signal.aborted) return;
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      throw new Error(json.message || '加载系统监控数据失败');
    }
    if (json.data) {
      overview.generated_at = json.data.generated_at || '';
      if (json.data.system_health) {
        Object.assign(overview.system_health, json.data.system_health);
      }
      if (json.data.telemetry) {
        Object.assign(overview.telemetry, json.data.telemetry);
      }
      if (json.data.business) {
        Object.assign(overview.business, json.data.business);
      }
      hasLoadedOnce.value = true;
    }
  } catch (err) {
    if (err?.name === 'AbortError' || isUnmounted) return;
    if (!silent) {
      errorMessage.value = err.message || '网络请求失败，请检查后端服务状态';
    }
  } finally {
    if (activeAbortController === controller) {
      activeAbortController = null;
      if (!isUnmounted) {
        isManualRefreshing.value = false;
        isSilentRefreshing.value = false;
      }
    }
  }
};

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const restartPolling = (intervalMs) => {
  stopPolling();
  if (!isUnmounted && intervalMs > 0) {
    pollTimer = setInterval(() => {
      loadOverview(true);
    }, intervalMs);
  }
};

watch(pollingIntervalMs, (nextVal) => {
  restartPolling(Number(nextVal || 0));
});

onMounted(() => {
  isUnmounted = false;
  loadOverview(false);
});

onBeforeUnmount(() => {
  isUnmounted = true;
  stopPolling();
  if (activeAbortController) {
    activeAbortController.abort();
    activeAbortController = null;
  }
});
</script>

<style scoped>
.viz-root {
  --viz-surface: #ffffff;
  --viz-ink-primary: #111827;
  --viz-ink-secondary: #4b5563;
  --viz-ink-muted: #6b7280;
  --viz-gridline: #e5e7eb;
  --viz-axis: #c3c2b7;
  --viz-series-1: #2a78d6;
  --viz-series-2: #eb6834;
}

.viz-root.viz-dark {
  --viz-surface: #0f172a;
  --viz-ink-primary: #f8fafc;
  --viz-ink-secondary: #94a3b8;
  --viz-ink-muted: #94a3b8;
  --viz-gridline: #2c2c2a;
  --viz-axis: #475569;
  --viz-series-1: #3987e5;
  --viz-series-2: #d95926;
}

.kpi-value {
  font-family: system-ui, -apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-variant-numeric: proportional-nums;
}

.tabular-svg-text {
  font-variant-numeric: tabular-nums;
}
</style>
