<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-6 lg:p-8 transition-colors duration-180">
    <div class="max-w-6xl w-full mx-auto space-y-6 pb-8">
      <!-- Top Header & Actions -->
      <header class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-start sm:items-center gap-3">
          <div class="w-10 h-10 rounded-xl bg-bg-surface border border-border-card flex items-center justify-center text-text-main shrink-0">
            <SlidersHorizontal class="w-5 h-5" />
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-base sm:text-lg font-semibold text-text-main tracking-tight">模型参数与节点配置</h1>
              <span class="px-2 py-0.5 rounded-md text-[10px] font-medium bg-bg-surface text-text-secondary border border-border-subtle inline-flex items-center gap-1">
                <ShieldCheck class="w-3 h-3" />
                <span>管理员专属</span>
              </span>
              <StatusMark
                :status="engineStatusLevel"
                :label="activeEngineLabel"
              />
            </div>
            <p class="text-xs text-text-muted mt-0.5">
              配置推理引擎、采样参数、检索截断阈值与系统指令，保存后实时生效
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2">
          <FuseButton
            variant="secondary"
            size="md"
            :loading="isProbing"
            :disabled="isLoading || isSaving"
            @click="runProbe"
          >
            <span class="inline-flex items-center gap-1.5">
              <Activity class="w-3.5 h-3.5 text-text-secondary" />
              <span>{{ isProbing ? '探活检测中...' : '连通性探活' }}</span>
            </span>
          </FuseButton>

          <HoldButton
            label="长按恢复默认"
            holding-label="继续按住以重置..."
            hint="长按 0.85 秒恢复启动基线配置"
            variant="danger"
            size="md"
            :disabled="isLoading || isSaving"
            @confirm="handleReset"
          >
            <template #icon>
              <RotateCcw class="w-3.5 h-3.5" />
            </template>
          </HoldButton>

          <FuseButton
            variant="primary"
            size="md"
            :loading="isSaving"
            :disabled="isLoading"
            @click="handleSave"
          >
            <span class="inline-flex items-center gap-1.5">
              <Save class="w-3.5 h-3.5" />
              <span>{{ isSaving ? '正在下发...' : '保存并生效' }}</span>
            </span>
          </FuseButton>

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
          class="px-4 py-3 rounded-xl border text-xs flex items-center justify-between gap-3 bg-bg-surface"
          :class="
            feedback.type === 'error'
              ? 'border-status-danger/40 text-status-danger'
              : 'border-border-strong text-text-main'
          "
        >
          <div class="flex items-center gap-2">
            <CheckCircle2 v-if="feedback.type !== 'error'" class="w-4 h-4 text-status-success shrink-0" />
            <span v-else class="w-2 h-2 rounded-full bg-status-danger shrink-0"></span>
            <span class="font-medium">{{ feedback.message }}</span>
          </div>
          <button
            type="button"
            @click="feedback.message = ''"
            class="p-1 rounded-md text-text-secondary hover:text-text-main hover:bg-bg-hover cursor-pointer transition-colors duration-150"
            aria-label="关闭提示"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </transition>

      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div class="lg:col-span-7 h-72 rounded-xl bg-bg-surface border border-border-subtle"></div>
        <div class="lg:col-span-5 h-72 rounded-xl bg-bg-surface border border-border-subtle"></div>
      </div>

      <!-- Main Config Grid -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <!-- Left Column (7 cols): Inference Engine, Thinking Mode & Sampling -->
        <div class="lg:col-span-7 space-y-6">
          <!-- Card 1: Inference Engine & Thinking Mode -->
          <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-5">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                  <Cpu class="w-4 h-4" />
                </div>
                <div>
                  <h2 class="text-sm font-semibold text-text-main">推理引擎与思考模式</h2>
                  <p class="text-[11px] text-text-muted">配置驱动引擎、接口端点与推理开关</p>
                </div>
              </div>

              <RubberSegment
                v-model="thinkingSegmentValue"
                :options="thinkingOptions"
              />
            </div>

            <!-- Thinking Mode Comparison Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <button
                type="button"
                @click="form.llm_thinking = false"
                class="btn-pressable p-3.5 rounded-lg border text-left cursor-pointer flex items-start gap-3"
                :class="
                  !form.llm_thinking
                    ? 'bg-bg-surface border-border-strong'
                    : 'bg-bg-card border-border-subtle hover:border-border-card'
                "
              >
                <div class="w-7 h-7 rounded-md bg-bg-card border border-border-subtle text-text-main flex items-center justify-center shrink-0 mt-0.5">
                  <Zap class="w-3.5 h-3.5" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="text-xs font-semibold text-text-main">极速模式</span>
                    <span
                      v-if="!form.llm_thinking"
                      class="px-1.5 py-0.5 rounded text-[9px] font-medium bg-action-primary text-action-primary-fg"
                    >
                      当前启用
                    </span>
                  </div>
                  <p class="text-[11px] text-text-muted mt-1 leading-relaxed">
                    关闭思考流输出，降低首字延迟，适合日常高效问答。
                  </p>
                </div>
              </button>

              <button
                type="button"
                @click="form.llm_thinking = true"
                class="btn-pressable p-3.5 rounded-lg border text-left cursor-pointer flex items-start gap-3"
                :class="
                  form.llm_thinking
                    ? 'bg-bg-surface border-border-strong'
                    : 'bg-bg-card border-border-subtle hover:border-border-card'
                "
              >
                <div class="w-7 h-7 rounded-md bg-bg-card border border-border-subtle text-text-main flex items-center justify-center shrink-0 mt-0.5">
                  <Layers class="w-3.5 h-3.5" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center gap-1.5">
                    <span class="text-xs font-semibold text-text-main">深度思考 (CoT)</span>
                    <span
                      v-if="form.llm_thinking"
                      class="px-1.5 py-0.5 rounded text-[9px] font-medium bg-action-primary text-action-primary-fg"
                    >
                      当前启用
                    </span>
                  </div>
                  <p class="text-[11px] text-text-muted mt-1 leading-relaxed">
                    启用思维链推理并同步折叠展示推理过程，适合复杂核查。
                  </p>
                </div>
              </button>
            </div>

            <!-- Provider Selector Grid -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label class="text-xs font-semibold text-text-main">模型驱动引擎 (LLM_PROVIDER)</label>
                <button
                  type="button"
                  @click="applySelectedProviderPreset"
                  class="text-[11px] text-text-secondary hover:text-text-main underline underline-offset-2 font-medium cursor-pointer transition-colors duration-150"
                >
                  应用推荐模型与端点
                </button>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                <button
                  v-for="prov in providers"
                  :key="prov.id"
                  type="button"
                  @click="selectProvider(prov)"
                  class="btn-pressable p-2.5 rounded-lg border text-left cursor-pointer space-y-1"
                  :class="
                    form.llm_provider === prov.id
                      ? 'bg-bg-surface border-border-strong text-text-main'
                      : 'bg-bg-card border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                  "
                >
                  <div class="flex items-center justify-between gap-1">
                    <span class="text-xs font-semibold truncate">{{ prov.label }}</span>
                    <Check
                      v-if="form.llm_provider === prov.id"
                      class="w-3.5 h-3.5 text-text-main shrink-0"
                    />
                  </div>
                  <p class="text-[10px] text-text-muted line-clamp-2 leading-snug">{{ prov.description }}</p>
                </button>
              </div>
            </div>

            <!-- Model & API Base -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
              <div class="space-y-1.5">
                <label for="admin-llm-model" class="block text-xs font-semibold text-text-main">
                  模型标识符 (LLM_MODEL)
                </label>
                <input
                  id="admin-llm-model"
                  v-model.trim="form.llm_model"
                  type="text"
                  placeholder="例如：qwen3.5:2b 或 deepseek-chat"
                  class="w-full px-3 py-2 rounded-lg bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150"
                />
              </div>

              <div class="space-y-1.5">
                <label for="admin-llm-base" class="block text-xs font-semibold text-text-main">
                  服务接口地址 (LLM_API_BASE)
                </label>
                <input
                  id="admin-llm-base"
                  v-model.trim="form.llm_api_base"
                  type="url"
                  placeholder="留空使用引擎默认端点或离线模式"
                  class="w-full px-3 py-2 rounded-lg bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150 font-mono"
                />
              </div>
            </div>

            <!-- Security Masked Credentials Zone -->
            <div class="p-4 rounded-lg bg-bg-surface border border-border-subtle space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-2">
                  <KeyRound class="w-4 h-4 text-text-secondary shrink-0" />
                  <span class="text-xs font-semibold text-text-main">凭据掩码状态（绝不回显明文）</span>
                </div>
                <span class="inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-md bg-bg-card text-text-secondary border border-border-subtle font-medium">
                  <span class="w-1.5 h-1.5 rounded-full bg-status-success"></span>
                  <span>掩码保护已启用</span>
                </span>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-[11px]">
                <div class="p-2.5 rounded-lg bg-bg-card border border-border-subtle flex items-center justify-between gap-2">
                  <span class="text-text-secondary">LLM API Key</span>
                  <span
                    class="font-mono font-semibold truncate"
                    :class="metaInfo.api_key_configured ? 'text-status-success' : 'text-text-muted'"
                  >
                    {{ metaInfo.api_key_masked }}
                  </span>
                </div>

                <div class="p-2.5 rounded-lg bg-bg-card border border-border-subtle flex items-center justify-between gap-2">
                  <span class="text-text-secondary">JWT 签名密钥</span>
                  <span class="font-mono font-semibold text-text-secondary truncate">
                    {{ metaInfo.jwt_secret_masked }}
                  </span>
                </div>
              </div>

              <div class="flex flex-col sm:flex-row sm:items-center gap-2.5">
                <input
                  v-model="writeOnlyApiKey"
                  type="password"
                  autocomplete="new-password"
                  :disabled="clearApiKey"
                  placeholder="输入新 API Key 以覆盖（留空保持不变）"
                  class="flex-1 px-3 py-2 rounded-lg bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus disabled:opacity-50 font-mono transition-colors duration-150"
                />
                <label
                  v-if="metaInfo.api_key_configured"
                  class="inline-flex items-center gap-1.5 text-[11px] text-status-danger cursor-pointer shrink-0 select-none"
                >
                  <input
                    v-model="clearApiKey"
                    type="checkbox"
                    class="rounded border-border-card accent-zinc-900 dark:accent-zinc-100"
                  />
                  <span>清空外部密钥</span>
                </label>
              </div>
            </div>
          </section>

          <!-- Card 2: Sampling & Token Budget -->
          <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-5">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                <Gauge class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-semibold text-text-main">采样与 Token 预算</h2>
                <p class="text-[11px] text-text-muted">平衡回答确定性与最大输出长度</p>
              </div>
            </div>

            <!-- Temperature Slider -->
            <div class="space-y-2">
              <div class="flex items-center justify-between gap-2">
                <label for="slider-temperature" class="text-xs font-semibold text-text-main">
                  采样温度 (Temperature)
                </label>
                <div class="flex items-center gap-1.5">
                  <button
                    v-for="preset in tempPresets"
                    :key="preset.value"
                    type="button"
                    @click="form.llm_temperature = preset.value"
                    class="btn-pressable px-2 py-0.5 rounded-md text-[10px] border cursor-pointer"
                    :class="
                      Math.abs(form.llm_temperature - preset.value) < 0.01
                        ? 'bg-action-primary text-action-primary-fg border-action-primary font-semibold'
                        : 'bg-bg-surface border-border-subtle text-text-secondary hover:text-text-main'
                    "
                  >
                    {{ preset.label }}
                  </button>
                  <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-xs font-mono tabular-nums font-semibold text-text-main min-w-[3.2rem] text-center">
                    {{ Number(form.llm_temperature).toFixed(2) }}
                  </span>
                </div>
              </div>
              <input
                id="slider-temperature"
                v-model.number="form.llm_temperature"
                type="range"
                min="0"
                max="2"
                step="0.05"
                class="w-full accent-zinc-900 dark:accent-zinc-100 cursor-pointer"
              />
              <div class="flex justify-between text-[10px] text-text-muted">
                <span>0.0 严谨确定</span>
                <span>1.0 均衡</span>
                <span>2.0 高发散</span>
              </div>
            </div>

            <!-- Max Tokens Slider -->
            <div class="space-y-2 pt-3 border-t border-border-subtle">
              <div class="flex items-center justify-between gap-2">
                <label for="slider-max-tokens" class="text-xs font-semibold text-text-main">
                  最大生成长度 (Max Tokens)
                </label>
                <div class="flex items-center gap-1.5">
                  <button
                    v-for="tk in [1024, 2048, 4096, 8192]"
                    :key="tk"
                    type="button"
                    @click="form.llm_max_tokens = tk"
                    class="btn-pressable px-2 py-0.5 rounded-md text-[10px] border font-mono tabular-nums cursor-pointer"
                    :class="
                      form.llm_max_tokens === tk
                        ? 'bg-action-primary text-action-primary-fg border-action-primary font-semibold'
                        : 'bg-bg-surface border-border-subtle text-text-secondary hover:text-text-main'
                    "
                  >
                    {{ tk }}
                  </button>
                  <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-xs font-mono tabular-nums font-semibold text-text-main min-w-[3.8rem] text-center">
                    {{ form.llm_max_tokens }}
                  </span>
                </div>
              </div>
              <input
                id="slider-max-tokens"
                v-model.number="form.llm_max_tokens"
                type="range"
                min="128"
                max="16384"
                step="128"
                class="w-full accent-zinc-900 dark:accent-zinc-100 cursor-pointer"
              />
              <div class="flex justify-between text-[10px] text-text-muted">
                <span>128 精简</span>
                <span>4096 推荐基准</span>
                <span>16384 超长</span>
              </div>
            </div>
          </section>

          <!-- Card 2.5: Cognitive Routing & Query Rewriting Policy -->
          <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-5">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center gap-2.5">
                <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                  <GitBranch class="w-4 h-4" />
                </div>
                <div>
                  <h2 class="text-sm font-semibold text-text-main">认知路由与改写策略</h2>
                  <p class="text-[11px] text-text-muted">独立控制内部非思考链路开关与超时回退阈值 (0.2s ~ 15.0s)</p>
                </div>
              </div>
              <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-[10px] font-medium text-text-secondary shrink-0">
                仅管理员可见
              </span>
            </div>

            <div class="space-y-4">
              <div
                v-for="(item, idx) in cognitiveStrategies"
                :key="item.key"
                class="space-y-2.5"
                :class="idx > 0 ? 'pt-4 border-t border-border-subtle' : ''"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="space-y-0.5 min-w-0">
                    <div class="text-xs font-semibold text-text-main">{{ item.title }}</div>
                    <p class="text-[11px] text-text-muted leading-relaxed">{{ item.description }}</p>
                  </div>
                  <button
                    type="button"
                    role="switch"
                    :aria-checked="form[item.enabledKey]"
                    @click="form[item.enabledKey] = !form[item.enabledKey]"
                    class="btn-pressable shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-medium border cursor-pointer"
                    :class="
                      form[item.enabledKey]
                        ? 'bg-action-primary text-action-primary-fg border-action-primary'
                        : 'bg-bg-surface text-text-secondary border-border-subtle hover:text-text-main'
                    "
                  >
                    <Check v-if="form[item.enabledKey]" class="w-3 h-3" />
                    <span>{{ form[item.enabledKey] ? '已启用 LLM' : '仅规则回退' }}</span>
                  </button>
                </div>

                <div class="space-y-1.5">
                  <div class="flex items-center justify-between gap-2">
                    <label :for="`slider-${item.key}-timeout`" class="text-[11px] font-medium text-text-secondary">
                      超时降级阈值
                    </label>
                    <div class="flex items-center gap-1.5">
                      <button
                        v-for="sec in cognitiveTimeoutPresets"
                        :key="`${item.key}-${sec}`"
                        type="button"
                        :disabled="!form[item.enabledKey]"
                        @click="form[item.timeoutKey] = sec"
                        class="btn-pressable px-2 py-0.5 rounded-md text-[10px] border font-mono tabular-nums cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                        :class="
                          Math.abs(Number(form[item.timeoutKey]) - sec) < 0.05
                            ? 'bg-action-primary text-action-primary-fg border-action-primary font-semibold'
                            : 'bg-bg-surface border-border-subtle text-text-secondary hover:text-text-main'
                        "
                      >
                        {{ sec.toFixed(1) }}s
                      </button>
                      <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-xs font-mono tabular-nums font-semibold text-text-main min-w-[3.4rem] text-center">
                        {{ Number(form[item.timeoutKey]).toFixed(1) }}s
                      </span>
                    </div>
                  </div>
                  <input
                    :id="`slider-${item.key}-timeout`"
                    v-model.number="form[item.timeoutKey]"
                    type="range"
                    min="0.2"
                    max="15"
                    step="0.1"
                    :disabled="!form[item.enabledKey]"
                    class="w-full accent-zinc-900 dark:accent-zinc-100 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                  />
                  <div class="flex justify-between text-[10px] text-text-muted tabular-nums">
                    <span>0.2s 极速回退</span>
                    <span>2.5s 默认基准</span>
                    <span>15.0s 宽松等待</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <!-- Right Column (5 cols): LangGraph & RAG Policy + Probe Diagnostics -->
        <div class="lg:col-span-5 space-y-6">
          <!-- Card 3: LangGraph & RAG Retrieval Policy -->
          <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-5">
            <div class="flex items-center gap-2.5">
              <div class="w-8 h-8 rounded-lg bg-bg-surface border border-border-subtle text-text-main flex items-center justify-center shrink-0">
                <Database class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-semibold text-text-main">LangGraph 节点与 RAG 检索策略</h2>
                <p class="text-[11px] text-text-muted">调节召回条数、重排阈值与行为指令</p>
              </div>
            </div>

            <!-- RAG Top-K -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label for="slider-top-k" class="text-xs font-semibold text-text-main">
                  混合检索召回片段数 (Top-K)
                </label>
                <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-xs font-mono tabular-nums font-semibold text-text-main">
                  {{ form.rag_top_k }} 条
                </span>
              </div>
              <input
                id="slider-top-k"
                v-model.number="form.rag_top_k"
                type="range"
                min="1"
                max="20"
                step="1"
                class="w-full accent-zinc-900 dark:accent-zinc-100 cursor-pointer"
              />
              <p class="text-[11px] text-text-muted">
                单次注入生成节点的制度片段数量，推荐 3~6 条。
              </p>
            </div>

            <!-- RAG Min Score -->
            <div class="space-y-2 pt-3 border-t border-border-subtle">
              <div class="flex items-center justify-between">
                <label for="slider-min-score" class="text-xs font-semibold text-text-main">
                  Rerank 置信度截断阈值 (min_score)
                </label>
                <span class="px-2 py-0.5 rounded-md bg-bg-surface border border-border-subtle text-xs font-mono tabular-nums font-semibold text-text-main">
                  {{ Number(form.rag_min_score).toFixed(2) }}
                </span>
              </div>
              <input
                id="slider-min-score"
                v-model.number="form.rag_min_score"
                type="range"
                min="0"
                max="1"
                step="0.02"
                class="w-full accent-zinc-900 dark:accent-zinc-100 cursor-pointer"
              />
              <p class="text-[11px] text-text-muted">
                低于该分数的切片自动过滤；全部未命中时触发防幻觉提示。
              </p>
            </div>

            <!-- System Behavioral Instruction -->
            <div class="space-y-2 pt-3 border-t border-border-subtle">
              <div class="flex items-center justify-between">
                <label for="admin-system-instruction" class="text-xs font-semibold text-text-main">
                  附加行为规范指令
                </label>
                <span class="text-[10px] font-mono tabular-nums text-text-muted">
                  {{ form.system_prompt_instruction.length }} / 2000
                </span>
              </div>

              <textarea
                id="admin-system-instruction"
                v-model="form.system_prompt_instruction"
                rows="4"
                maxlength="2000"
                placeholder="例如：涉及财务报销与采购金额时，优先使用表格列出审批层级与单据清单。"
                class="w-full p-3 rounded-lg bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors duration-150 resize-y leading-relaxed"
              ></textarea>

              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="tpl in instructionPresets"
                  :key="tpl.label"
                  type="button"
                  @click="form.system_prompt_instruction = tpl.text"
                  class="btn-pressable px-2.5 py-1 rounded-md bg-bg-surface hover:bg-bg-hover border border-border-subtle text-[10px] text-text-secondary hover:text-text-main cursor-pointer"
                >
                  {{ tpl.label }}
                </button>
              </div>
            </div>
          </section>

          <!-- Card 4: Live Connectivity Probe & Audit Telemetry -->
          <section class="rounded-xl bg-bg-card border border-border-card p-5 sm:p-6 space-y-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <Activity class="w-4 h-4 text-text-secondary" />
                <h2 class="text-sm font-semibold text-text-main">端点连通性探活</h2>
              </div>
              <button
                type="button"
                :disabled="isProbing"
                @click="runProbe"
                class="text-[11px] font-medium text-text-secondary hover:text-text-main underline underline-offset-2 cursor-pointer disabled:opacity-50 transition-colors duration-150"
              >
                {{ isProbing ? '探测中...' : '立即探测' }}
              </button>
            </div>

            <div
              v-if="probeResult"
              class="p-4 rounded-lg border bg-bg-surface space-y-3"
              :class="probeResult.reachable ? 'border-border-strong' : 'border-status-approval/50'"
            >
              <div class="flex items-center justify-between gap-2">
                <StatusMark
                  :status="probeResult.reachable ? 'success' : 'warning'"
                  :label="probeResult.status"
                />
                <span class="text-[11px] font-mono tabular-nums text-text-secondary">
                  {{ probeResult.latency_ms }} ms
                </span>
              </div>

              <p class="text-xs text-text-main leading-relaxed">{{ probeResult.detail }}</p>

              <div class="grid grid-cols-2 gap-2 text-[11px]">
                <div class="p-2.5 rounded-lg bg-bg-card border border-border-subtle">
                  <div class="text-text-muted text-[10px]">探测端点</div>
                  <div class="font-mono text-text-main truncate mt-0.5">{{ probeResult.endpoint }}</div>
                </div>
                <div class="p-2.5 rounded-lg bg-bg-card border border-border-subtle">
                  <div class="text-text-muted text-[10px]">Qdrant 切片</div>
                  <div class="font-mono tabular-nums text-text-main mt-0.5">
                    {{ probeResult.rag_points }} 条 ({{ probeResult.rag_status }})
                  </div>
                </div>
              </div>

              <div v-if="probeResult.available_models && probeResult.available_models.length > 0" class="space-y-1.5">
                <div class="text-[10px] text-text-secondary font-medium">在线模型（点击填入）：</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="m in probeResult.available_models"
                    :key="m"
                    type="button"
                    @click="form.llm_model = m"
                    class="btn-pressable px-2 py-0.5 rounded-md text-[10px] font-mono bg-bg-card border border-border-card hover:border-border-strong text-text-main cursor-pointer"
                  >
                    {{ m }}
                  </button>
                </div>
              </div>
            </div>

            <div
              v-else
              class="p-4 rounded-lg bg-bg-surface border border-border-subtle text-xs text-text-muted leading-relaxed"
            >
              点击「连通性探活」可验证当前端点与本地向量索引状态。
            </div>

            <!-- Last Audit Metadata -->
            <div class="pt-3 border-t border-border-subtle flex flex-wrap items-center justify-between gap-2 text-[11px] text-text-muted">
              <span>引擎：{{ metaInfo.active_engine || 'LocalEnterpriseChatModel' }}</span>
              <span class="tabular-nums">
                变更：{{ formattedUpdatedAt }}
                <template v-if="metaInfo.updated_by"> ({{ metaInfo.updated_by }})</template>
              </span>
            </div>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import {
  SlidersHorizontal,
  ShieldCheck,
  Activity,
  RotateCcw,
  Save,
  MessageSquare,
  CheckCircle2,
  X,
  Cpu,
  Zap,
  Layers,
  Check,
  KeyRound,
  Gauge,
  Database,
  GitBranch,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import FuseButton from '../components/ui/FuseButton.vue';
import HoldButton from '../components/ui/HoldButton.vue';
import RubberSegment from '../components/ui/RubberSegment.vue';
import StatusMark from '../components/ui/StatusMark.vue';

const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(true);
const isSaving = ref(false);
const isProbing = ref(false);
const writeOnlyApiKey = ref('');
const clearApiKey = ref(false);
const probeResult = ref(null);
const providers = ref([]);

const feedback = reactive({
  type: 'success',
  message: '',
});

const form = reactive({
  llm_provider: 'auto',
  llm_model: 'deepseek-chat',
  llm_api_base: '',
  llm_thinking: false,
  llm_temperature: 0.2,
  llm_max_tokens: 4096,
  rag_top_k: 3,
  rag_min_score: 0.16,
  system_prompt_instruction: '',
  router_llm_enabled: true,
  router_llm_timeout: 2.5,
  query_rewriter_llm_enabled: true,
  query_rewriter_llm_timeout: 2.5,
  slot_extractor_llm_enabled: true,
  slot_extractor_llm_timeout: 2.5,
});

const cognitiveTimeoutPresets = [1.5, 2.5, 5.0];

const cognitiveStrategies = [
  {
    key: 'router',
    title: '认知意图路由',
    description: '多轮语境意图识别与复合流程判定，超时自动回退本地规则路由。',
    enabledKey: 'router_llm_enabled',
    timeoutKey: 'router_llm_timeout',
  },
  {
    key: 'rewriter',
    title: '语境查询改写',
    description: '多轮指代消解与跨领域检索子查询改写，超时自动降级至确定性规则。',
    enabledKey: 'query_rewriter_llm_enabled',
    timeoutKey: 'query_rewriter_llm_timeout',
  },
  {
    key: 'slots',
    title: '语义槽位提取',
    description: '业务工具与审批参数混合抽取，缺失必填参数时通过自然语言澄清。',
    enabledKey: 'slot_extractor_llm_enabled',
    timeoutKey: 'slot_extractor_llm_timeout',
  },
];

const clampTimeout = (val, fallback = 2.5) => {
  const num = Number(val);
  if (!Number.isFinite(num)) return fallback;
  return Math.min(15.0, Math.max(0.2, Math.round(num * 10) / 10));
};

const metaInfo = reactive({
  api_key_configured: false,
  api_key_masked: '未配置',
  jwt_secret_configured: true,
  jwt_secret_masked: '****** (HS256 已启用保护)',
  active_engine: 'LocalEnterpriseChatModel',
  updated_at: null,
  updated_by: null,
});

const thinkingOptions = [
  { value: 'fast', label: '极速模式', icon: Zap },
  { value: 'deep', label: '深度思考', icon: Layers },
];

const thinkingSegmentValue = computed({
  get: () => (form.llm_thinking ? 'deep' : 'fast'),
  set: (val) => {
    form.llm_thinking = val === 'deep';
  },
});

const tempPresets = [
  { label: '0.1 严谨', value: 0.1 },
  { label: '0.2 默认', value: 0.2 },
  { label: '0.7 灵活', value: 0.7 },
];

const instructionPresets = [
  {
    label: '严谨合规与结构化表格',
    text: '回答财务报销与采购审批问题时，优先列出金额区间、审批人层级与必备单据清单，确保术语严谨准确。',
  },
  {
    label: '简洁重点提炼',
    text: '回答应先给出明确结论，再用编号条列核心依据与操作路径，避免冗余寒暄。',
  },
  {
    label: '清空指令',
    text: '',
  },
];

const engineStatusLevel = computed(() => {
  if (metaInfo.active_engine === 'LocalEnterpriseChatModel') return 'idle';
  return 'success';
});

const activeEngineLabel = computed(() => {
  const modeLabel = form.llm_thinking ? '深度思考 CoT' : '极速模式';
  return `${metaInfo.active_engine} · ${modeLabel}`;
});

const formattedUpdatedAt = computed(() => {
  if (!metaInfo.updated_at) return '启动基线默认';
  try {
    return new Date(metaInfo.updated_at).toLocaleString('zh-CN');
  } catch {
    return metaInfo.updated_at;
  }
});

const showFeedback = (type, message) => {
  feedback.type = type;
  feedback.message = message;
};

const applyServerPayload = (data) => {
  if (!data) return;
  form.llm_provider = data.llm_provider || 'auto';
  form.llm_model = data.llm_model || 'deepseek-chat';
  form.llm_api_base = data.llm_api_base || '';
  form.llm_thinking = Boolean(data.llm_thinking);
  form.llm_temperature = Number(data.llm_temperature ?? 0.2);
  form.llm_max_tokens = Number(data.llm_max_tokens ?? 4096);
  form.rag_top_k = Number(data.rag_top_k ?? 3);
  form.rag_min_score = Number(data.rag_min_score ?? 0.16);
  form.system_prompt_instruction = data.system_prompt_instruction || '';
  form.router_llm_enabled = data.router_llm_enabled !== undefined ? Boolean(data.router_llm_enabled) : true;
  form.router_llm_timeout = clampTimeout(data.router_llm_timeout ?? 2.5, 2.5);
  form.query_rewriter_llm_enabled = data.query_rewriter_llm_enabled !== undefined ? Boolean(data.query_rewriter_llm_enabled) : true;
  form.query_rewriter_llm_timeout = clampTimeout(data.query_rewriter_llm_timeout ?? 2.5, 2.5);
  form.slot_extractor_llm_enabled = data.slot_extractor_llm_enabled !== undefined ? Boolean(data.slot_extractor_llm_enabled) : true;
  form.slot_extractor_llm_timeout = clampTimeout(data.slot_extractor_llm_timeout ?? 2.5, 2.5);

  metaInfo.api_key_configured = Boolean(data.api_key_configured);
  metaInfo.api_key_masked = data.api_key_masked || '未配置';
  metaInfo.jwt_secret_configured = Boolean(data.jwt_secret_configured);
  metaInfo.jwt_secret_masked = data.jwt_secret_masked || '******';
  metaInfo.active_engine = data.active_engine || 'LocalEnterpriseChatModel';
  metaInfo.updated_at = data.updated_at || null;
  metaInfo.updated_by = data.updated_by || null;

  if (Array.isArray(data.providers)) {
    providers.value = data.providers;
  }

  writeOnlyApiKey.value = '';
  clearApiKey.value = false;
};

const handleAuthFailure = (status, message) => {
  if (status === 401) {
    authStore.handleUnauthorized();
    router.replace({ path: '/login', query: { redirect: '/admin/settings' } });
    return true;
  }
  if (status === 403) {
    authStore.setPermissionNotice(message || '权限不足：模型与节点配置中心仅限系统管理员访问。');
    router.replace('/');
    return true;
  }
  return false;
};

const loadConfig = async () => {
  isLoading.value = true;
  try {
    const resp = await fetch('/api/v1/admin/config', {
      headers: authStore.getAuthHeaders(),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      showFeedback('error', json.message || '加载管理员配置失败');
      return;
    }
    applyServerPayload(json.data);
  } catch (err) {
    showFeedback('error', err.message || '无法连接后端配置接口，请确认服务正常运行');
  } finally {
    isLoading.value = false;
  }
};

const selectProvider = (prov) => {
  form.llm_provider = prov.id;
  const knownDefaultModels = new Set(providers.value.map((p) => p.default_model).filter(Boolean));
  const knownDefaultBases = new Set(providers.value.map((p) => p.default_api_base || ''));
  if (!form.llm_model || knownDefaultModels.has(form.llm_model)) {
    form.llm_model = prov.default_model || form.llm_model;
  }
  if (!form.llm_api_base || knownDefaultBases.has(form.llm_api_base)) {
    form.llm_api_base = prov.default_api_base || '';
  }
  if (!prov.supports_thinking) {
    form.llm_thinking = false;
  }
};

const applySelectedProviderPreset = () => {
  const match = providers.value.find((p) => p.id === form.llm_provider);
  if (!match) return;
  if (match.default_model) {
    form.llm_model = match.default_model;
  }
  form.llm_api_base = match.default_api_base || '';
  if (!match.supports_thinking) {
    form.llm_thinking = false;
  }
  showFeedback('success', `已填充「${match.label}」推荐模型与默认端口，请核对后点击「保存并生效」`);
};

const handleSave = async () => {
  if (!form.llm_model || !form.llm_model.trim()) {
    showFeedback('error', '模型标识符 (LLM_MODEL) 不能为空');
    return;
  }
  isSaving.value = true;
  feedback.message = '';
  try {
    const payload = {
      llm_provider: form.llm_provider,
      llm_model: form.llm_model,
      llm_api_base: form.llm_api_base || '',
      llm_thinking: form.llm_thinking,
      llm_temperature: Number(form.llm_temperature),
      llm_max_tokens: Number(form.llm_max_tokens),
      rag_top_k: Number(form.rag_top_k),
      rag_min_score: Number(form.rag_min_score),
      system_prompt_instruction: form.system_prompt_instruction,
      router_llm_enabled: Boolean(form.router_llm_enabled),
      router_llm_timeout: clampTimeout(form.router_llm_timeout, 2.5),
      query_rewriter_llm_enabled: Boolean(form.query_rewriter_llm_enabled),
      query_rewriter_llm_timeout: clampTimeout(form.query_rewriter_llm_timeout, 2.5),
      slot_extractor_llm_enabled: Boolean(form.slot_extractor_llm_enabled),
      slot_extractor_llm_timeout: clampTimeout(form.slot_extractor_llm_timeout, 2.5),
      clear_api_key: clearApiKey.value,
    };

    if (writeOnlyApiKey.value.trim() && !clearApiKey.value) {
      payload.llm_api_key = writeOnlyApiKey.value.trim();
    }

    const resp = await fetch('/api/v1/admin/config', {
      method: 'PUT',
      headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      const detailMsg = Array.isArray(json.detail)
        ? json.detail.map((d) => d.msg).join('；')
        : json.message;
      showFeedback('error', detailMsg || '配置保存失败，请检查输入参数格式');
      return;
    }

    applyServerPayload(json.data);
    showFeedback('success', '配置已保存并在后端 LLM 工厂与 LangGraph 节点中实时热生效');
  } catch (err) {
    showFeedback('error', err.message || '保存请求异常');
  } finally {
    isSaving.value = false;
  }
};

const handleReset = async () => {
  isSaving.value = true;
  feedback.message = '';
  try {
    const resp = await fetch('/api/v1/admin/config/reset', {
      method: 'POST',
      headers: authStore.getAuthHeaders(),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      showFeedback('error', json.message || '恢复默认配置失败');
      return;
    }
    applyServerPayload(json.data);
    probeResult.value = null;
    showFeedback('success', '已恢复为系统启动基线默认配置');
  } catch (err) {
    showFeedback('error', err.message || '重置请求异常');
  } finally {
    isSaving.value = false;
  }
};

const runProbe = async () => {
  isProbing.value = true;
  try {
    const resp = await fetch('/api/v1/admin/config/probe', {
      method: 'POST',
      headers: authStore.getAuthHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        llm_provider: form.llm_provider,
        llm_model: form.llm_model,
        llm_api_base: form.llm_api_base || '',
        llm_thinking: form.llm_thinking,
      }),
    });
    const json = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      if (handleAuthFailure(resp.status, json.message)) return;
      showFeedback('error', json.message || '连通性探测失败');
      return;
    }
    probeResult.value = json.data;
  } catch (err) {
    showFeedback('error', err.message || '连通性探活请求异常');
  } finally {
    isProbing.value = false;
  }
};

onMounted(() => {
  loadConfig();
});
</script>
