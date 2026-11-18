<template>
  <div class="h-full flex-1 flex flex-col bg-bg-main overflow-y-auto p-4 sm:p-6 lg:p-8 transition-colors duration-200">
    <div class="max-w-6xl w-full mx-auto space-y-6 pb-8">
      <!-- Top Header & Actions -->
      <header class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-5 border-b border-border-subtle">
        <div class="flex items-start sm:items-center space-x-3">
          <div class="w-11 h-11 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0 shadow-sm">
            <SlidersHorizontal class="w-5 h-5" />
          </div>
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <h1 class="text-base sm:text-lg font-bold text-text-main">大模型参数与节点配置中心</h1>
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 inline-flex items-center space-x-1">
                <ShieldCheck class="w-3 h-3" />
                <span>管理员专属域</span>
              </span>
              <StatusMark
                :status="engineStatusLevel"
                :label="activeEngineLabel"
              />
            </div>
            <p class="text-xs text-text-secondary mt-1">
              统筹推理模式、采样参数、RAG 检索截断门限与系统级行为指令，保存后全链路实时生效
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
            <span class="inline-flex items-center space-x-1.5">
              <Activity class="w-3.5 h-3.5 text-brand-primary" />
              <span>{{ isProbing ? '探活检测中...' : '连通性探活' }}</span>
            </span>
          </FuseButton>

          <FuseButton
            v-if="!confirmReset"
            variant="ghost"
            size="md"
            :disabled="isLoading || isSaving"
            @click="confirmReset = true"
          >
            <span class="inline-flex items-center space-x-1.5">
              <RotateCcw class="w-3.5 h-3.5" />
              <span>恢复默认</span>
            </span>
          </FuseButton>

          <div v-else class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-rose-500/10 border border-rose-500/30">
            <span class="text-[11px] text-rose-700 dark:text-rose-300 font-medium">确认重置为启动基线？</span>
            <button
              type="button"
              :disabled="isSaving"
              @click="handleReset"
              class="px-2 py-0.5 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-semibold cursor-pointer disabled:opacity-50"
            >
              确认
            </button>
            <button
              type="button"
              @click="confirmReset = false"
              class="px-2 py-0.5 rounded-lg text-[11px] text-text-secondary hover:text-text-main cursor-pointer"
            >
              取消
            </button>
          </div>

          <FuseButton
            variant="primary"
            size="md"
            :loading="isSaving"
            :disabled="isLoading"
            @click="handleSave"
          >
            <span class="inline-flex items-center space-x-1.5">
              <Save class="w-3.5 h-3.5" />
              <span>{{ isSaving ? '正在下发...' : '保存并生效' }}</span>
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

      <!-- Feedback Banner -->
      <transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 -translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 -translate-y-1"
      >
        <div
          v-if="feedback.message"
          class="px-4 py-3 rounded-2xl border text-xs flex items-center justify-between gap-3 shadow-sm"
          :class="
            feedback.type === 'error'
              ? 'bg-rose-500/10 border-rose-500/35 text-rose-700 dark:text-rose-300'
              : 'bg-emerald-500/10 border-emerald-500/35 text-emerald-700 dark:text-emerald-300'
          "
        >
          <div class="flex items-center space-x-2">
            <component
              :is="feedback.type === 'error' ? AlertCircle : CheckCircle2"
              class="w-4 h-4 shrink-0"
            />
            <span class="font-medium">{{ feedback.message }}</span>
          </div>
          <button
            type="button"
            @click="feedback.message = ''"
            class="p-1 rounded-lg hover:bg-black/10 dark:hover:bg-white/10 cursor-pointer"
          >
            <X class="w-3.5 h-3.5" />
          </button>
        </div>
      </transition>

      <!-- Loading Skeleton -->
      <div v-if="isLoading" class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div class="lg:col-span-7 h-72 rounded-3xl glass-card border border-border-card animate-pulse"></div>
        <div class="lg:col-span-5 h-72 rounded-3xl glass-card border border-border-card animate-pulse"></div>
      </div>

      <!-- Main Config Grid -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <!-- Left Column (7 cols): Inference Engine, Thinking Mode & Sampling -->
        <div class="lg:col-span-7 space-y-5">
          <!-- Card 1: Inference Engine & Thinking Mode -->
          <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-5 shadow-md">
            <div class="flex items-center justify-between gap-2">
              <div class="flex items-center space-x-2.5">
                <div class="w-8 h-8 rounded-xl bg-brand-primary/10 text-brand-primary flex items-center justify-center">
                  <Cpu class="w-4 h-4" />
                </div>
                <div>
                  <h2 class="text-sm font-bold text-text-main">推理引擎与思考模式</h2>
                  <p class="text-[11px] text-text-muted">配置模型驱动适配器、接入端点与思维链推理开关</p>
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
                class="p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex items-start space-x-3"
                :class="
                  !form.llm_thinking
                    ? 'bg-brand-primary/10 border-brand-primary/50 shadow-sm'
                    : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle hover:border-border-card'
                "
              >
                <div class="w-8 h-8 rounded-xl bg-amber-500/15 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Zap class="w-4 h-4" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center space-x-1.5">
                    <span class="text-xs font-bold text-text-main">极速响应模式</span>
                    <span
                      v-if="!form.llm_thinking"
                      class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-brand-primary text-white"
                    >
                      当前启用
                    </span>
                  </div>
                  <p class="text-[11px] text-text-secondary mt-1 leading-relaxed">
                    关闭冗余思考流输出，大幅降低首字延迟（实测约 2.8s 响应），适合日常高效问答。
                  </p>
                </div>
              </button>

              <button
                type="button"
                @click="form.llm_thinking = true"
                class="p-3.5 rounded-2xl border text-left transition-all cursor-pointer flex items-start space-x-3"
                :class="
                  form.llm_thinking
                    ? 'bg-emerald-500/10 border-emerald-500/50 shadow-sm'
                    : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle hover:border-border-card'
                "
              >
                <div class="w-8 h-8 rounded-xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles class="w-4 h-4" />
                </div>
                <div class="min-w-0">
                  <div class="flex items-center space-x-1.5">
                    <span class="text-xs font-bold text-text-main">深度思考模式 (CoT)</span>
                    <span
                      v-if="form.llm_thinking"
                      class="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-600 text-white"
                    >
                      当前启用
                    </span>
                  </div>
                  <p class="text-[11px] text-text-secondary mt-1 leading-relaxed">
                    激活原生思维链推理并将推理轨迹同步至 ThoughtLine 折叠栏，适合复杂合规核查。
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
                  class="text-[11px] text-brand-primary hover:underline font-medium cursor-pointer"
                >
                  应用当前引擎推荐模型与端点
                </button>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                <button
                  v-for="prov in providers"
                  :key="prov.id"
                  type="button"
                  @click="selectProvider(prov)"
                  class="p-2.5 rounded-xl border text-left transition-all cursor-pointer space-y-1"
                  :class="
                    form.llm_provider === prov.id
                      ? 'bg-brand-primary/10 border-brand-primary/50 text-text-main shadow-sm'
                      : 'bg-slate-100/70 dark:bg-slate-900/60 border-border-subtle text-text-secondary hover:text-text-main hover:border-border-card'
                  "
                >
                  <div class="flex items-center justify-between gap-1">
                    <span class="text-xs font-semibold truncate">{{ prov.label }}</span>
                    <Check
                      v-if="form.llm_provider === prov.id"
                      class="w-3.5 h-3.5 text-brand-primary shrink-0"
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
                  class="w-full px-3 py-2 rounded-xl bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors"
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
                  class="w-full px-3 py-2 rounded-xl bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors font-mono"
                />
              </div>
            </div>

            <!-- Security Masked Credentials Zone -->
            <div class="p-4 rounded-2xl bg-slate-100/80 dark:bg-slate-900/70 border border-border-subtle space-y-3">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center space-x-2">
                  <KeyRound class="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                  <span class="text-xs font-bold text-text-main">敏感凭据掩码状态（绝不回显明文）</span>
                </div>
                <span class="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/25 font-medium">
                  零明文外泄保护已启用
                </span>
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-[11px]">
                <div class="p-2.5 rounded-xl bg-bg-card border border-border-subtle flex items-center justify-between gap-2">
                  <span class="text-text-secondary">LLM API Key</span>
                  <span
                    class="font-mono font-semibold truncate"
                    :class="metaInfo.api_key_configured ? 'text-emerald-600 dark:text-emerald-400' : 'text-text-muted'"
                  >
                    {{ metaInfo.api_key_masked }}
                  </span>
                </div>

                <div class="p-2.5 rounded-xl bg-bg-card border border-border-subtle flex items-center justify-between gap-2">
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
                  placeholder="如需更新 API Key 请在此输入（留空或勾选清空以外保持原密钥不变）"
                  class="flex-1 px-3 py-2 rounded-xl bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus disabled:opacity-50 font-mono"
                />
                <label
                  v-if="metaInfo.api_key_configured"
                  class="inline-flex items-center space-x-1.5 text-[11px] text-rose-600 dark:text-rose-400 cursor-pointer shrink-0 select-none"
                >
                  <input
                    v-model="clearApiKey"
                    type="checkbox"
                    class="rounded border-border-card text-rose-600 focus:ring-rose-500"
                  />
                  <span>清空外部密钥</span>
                </label>
              </div>
            </div>
          </section>

          <!-- Card 2: Sampling & Token Budget -->
          <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-5 shadow-md">
            <div class="flex items-center space-x-2.5">
              <div class="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                <Gauge class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-bold text-text-main">生成采样与 Token 预算控制</h2>
                <p class="text-[11px] text-text-muted">平衡制度回答的确定性与长推理输出的上下文空间</p>
              </div>
            </div>

            <!-- Temperature Slider -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label for="slider-temperature" class="text-xs font-semibold text-text-main">
                  采样温度 (Temperature)
                </label>
                <div class="flex items-center space-x-1.5">
                  <button
                    v-for="preset in tempPresets"
                    :key="preset.value"
                    type="button"
                    @click="form.llm_temperature = preset.value"
                    class="px-2 py-0.5 rounded-lg text-[10px] border transition-colors cursor-pointer"
                    :class="
                      Math.abs(form.llm_temperature - preset.value) < 0.01
                        ? 'bg-brand-primary/15 border-brand-primary/40 text-brand-primary font-semibold'
                        : 'bg-slate-100 dark:bg-slate-900 border-border-subtle text-text-secondary hover:text-text-main'
                    "
                  >
                    {{ preset.label }}
                  </button>
                  <span class="px-2 py-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 text-xs font-mono font-bold text-text-main min-w-[3.2rem] text-center">
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
                class="w-full accent-brand-primary cursor-pointer"
              />
              <div class="flex justify-between text-[10px] text-text-muted">
                <span>0.0 绝对确定（规章制度严格引用）</span>
                <span>1.0 标准均衡</span>
                <span>2.0 高发散度</span>
              </div>
            </div>

            <!-- Max Tokens Slider -->
            <div class="space-y-2 pt-2 border-t border-border-subtle/70">
              <div class="flex items-center justify-between">
                <label for="slider-max-tokens" class="text-xs font-semibold text-text-main">
                  最大生成长度 (Max Tokens)
                </label>
                <div class="flex items-center space-x-1.5">
                  <button
                    v-for="tk in [1024, 2048, 4096, 8192]"
                    :key="tk"
                    type="button"
                    @click="form.llm_max_tokens = tk"
                    class="px-2 py-0.5 rounded-lg text-[10px] border font-mono transition-colors cursor-pointer"
                    :class="
                      form.llm_max_tokens === tk
                        ? 'bg-brand-primary/15 border-brand-primary/40 text-brand-primary font-semibold'
                        : 'bg-slate-100 dark:bg-slate-900 border-border-subtle text-text-secondary hover:text-text-main'
                    "
                  >
                    {{ tk }}
                  </button>
                  <span class="px-2 py-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 text-xs font-mono font-bold text-text-main min-w-[3.8rem] text-center">
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
                class="w-full accent-brand-primary cursor-pointer"
              />
              <div class="flex justify-between text-[10px] text-text-muted">
                <span>128 精简短答</span>
                <span>4096 推荐基准（满足 CoT 思考 + 正文输出）</span>
                <span>16384 超长输出</span>
              </div>
            </div>
          </section>
        </div>

        <!-- Right Column (5 cols): LangGraph & RAG Policy + Probe Diagnostics -->
        <div class="lg:col-span-5 space-y-5">
          <!-- Card 3: LangGraph & RAG Retrieval Policy -->
          <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-5 shadow-md">
            <div class="flex items-center space-x-2.5">
              <div class="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <Database class="w-4 h-4" />
              </div>
              <div>
                <h2 class="text-sm font-bold text-text-main">LangGraph 节点与 RAG 检索策略</h2>
                <p class="text-[11px] text-text-muted">动态调节 Retrieve 召回粒度、Rerank 截断线与规范指令</p>
              </div>
            </div>

            <!-- RAG Top-K -->
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <label for="slider-top-k" class="text-xs font-semibold text-text-main">
                  混合检索召回片段数 (Top-K)
                </label>
                <span class="px-2 py-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 text-xs font-mono font-bold text-text-main">
                  {{ form.rag_top_k }} 条制度切片
                </span>
              </div>
              <input
                id="slider-top-k"
                v-model.number="form.rag_top_k"
                type="range"
                min="1"
                max="20"
                step="1"
                class="w-full accent-emerald-600 cursor-pointer"
              />
              <p class="text-[11px] text-text-muted leading-relaxed">
                控制检索节点 (retrieve_node) 单次注入生成节点的规章上下文规模；推荐 3~6 条以兼顾精确率与首字延迟。
              </p>
            </div>

            <!-- RAG Min Score -->
            <div class="space-y-2 pt-2 border-t border-border-subtle/70">
              <div class="flex items-center justify-between">
                <label for="slider-min-score" class="text-xs font-semibold text-text-main">
                  Rerank 置信度截断阈值 (min_score)
                </label>
                <span class="px-2 py-0.5 rounded-lg bg-slate-200/70 dark:bg-slate-800 text-xs font-mono font-bold text-text-main">
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
                class="w-full accent-emerald-600 cursor-pointer"
              />
              <p class="text-[11px] text-text-muted leading-relaxed">
                低于该语义重排分数的制度切片将被自动过滤；若全部不达标，生成节点将触发合规自反思防幻觉提示。
              </p>
            </div>

            <!-- System Behavioral Instruction -->
            <div class="space-y-2 pt-2 border-t border-border-subtle/70">
              <div class="flex items-center justify-between">
                <label for="admin-system-instruction" class="text-xs font-semibold text-text-main">
                  企业数字员工附加行为规范指令
                </label>
                <span class="text-[10px] font-mono text-text-muted">
                  {{ form.system_prompt_instruction.length }} / 2000
                </span>
              </div>

              <textarea
                id="admin-system-instruction"
                v-model="form.system_prompt_instruction"
                rows="4"
                maxlength="2000"
                placeholder="例如：凡涉及财务报销与采购金额，均须使用加粗表格列出审批层级与单据清单，严禁省略合规免责声明。"
                class="w-full p-3 rounded-2xl bg-bg-input border border-border-card text-xs text-text-main placeholder:text-text-muted focus:outline-none focus:border-border-focus transition-colors resize-y leading-relaxed"
              ></textarea>

              <div class="flex flex-wrap gap-1.5">
                <button
                  v-for="tpl in instructionPresets"
                  :key="tpl.label"
                  type="button"
                  @click="form.system_prompt_instruction = tpl.text"
                  class="px-2.5 py-1 rounded-lg bg-slate-100 dark:bg-slate-900 hover:bg-slate-200/70 dark:hover:bg-slate-800 border border-border-subtle text-[10px] text-text-secondary hover:text-text-main transition-colors cursor-pointer"
                >
                  {{ tpl.label }}
                </button>
              </div>
            </div>
          </section>

          <!-- Card 4: Live Connectivity Probe & Audit Telemetry -->
          <section class="rounded-3xl glass-card border border-border-card p-5 sm:p-6 space-y-4 shadow-md">
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <Activity class="w-4 h-4 text-brand-primary" />
                <h2 class="text-sm font-bold text-text-main">端点连通性探活与生效状态</h2>
              </div>
              <button
                type="button"
                :disabled="isProbing"
                @click="runProbe"
                class="text-[11px] font-medium text-brand-primary hover:underline cursor-pointer disabled:opacity-50"
              >
                {{ isProbing ? '探测中...' : '立即探测' }}
              </button>
            </div>

            <div
              v-if="probeResult"
              class="p-4 rounded-2xl border space-y-3"
              :class="
                probeResult.reachable
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-amber-500/10 border-amber-500/30'
              "
            >
              <div class="flex items-center justify-between gap-2">
                <StatusMark
                  :status="probeResult.reachable ? 'success' : 'warning'"
                  :label="probeResult.status"
                />
                <span class="text-[11px] font-mono text-text-secondary">
                  耗时 {{ probeResult.latency_ms }} ms
                </span>
              </div>

              <p class="text-xs text-text-main leading-relaxed">{{ probeResult.detail }}</p>

              <div class="grid grid-cols-2 gap-2 text-[11px]">
                <div class="p-2 rounded-xl bg-bg-card/80 border border-border-subtle">
                  <div class="text-text-muted text-[10px]">探测端点</div>
                  <div class="font-mono text-text-main truncate mt-0.5">{{ probeResult.endpoint }}</div>
                </div>
                <div class="p-2 rounded-xl bg-bg-card/80 border border-border-subtle">
                  <div class="text-text-muted text-[10px]">Qdrant 知识切片</div>
                  <div class="font-mono text-text-main mt-0.5">
                    {{ probeResult.rag_points }} 条 ({{ probeResult.rag_status }})
                  </div>
                </div>
              </div>

              <div v-if="probeResult.available_models && probeResult.available_models.length > 0" class="space-y-1.5">
                <div class="text-[10px] text-text-secondary font-medium">已发现在线模型（点击快速填入）：</div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="m in probeResult.available_models"
                    :key="m"
                    type="button"
                    @click="form.llm_model = m"
                    class="px-2 py-0.5 rounded-lg text-[10px] font-mono bg-bg-card border border-border-subtle hover:border-brand-primary text-text-main cursor-pointer transition-colors"
                  >
                    {{ m }}
                  </button>
                </div>
              </div>
            </div>

            <div
              v-else
              class="p-4 rounded-2xl bg-slate-100/70 dark:bg-slate-900/60 border border-border-subtle text-xs text-text-secondary leading-relaxed"
            >
              点击右上角「连通性探活」可验证当前表单所选模型端点、思考模式及本地 Qdrant 向量索引是否处于就绪状态。
            </div>

            <!-- Last Audit Metadata -->
            <div class="pt-3 border-t border-border-subtle flex flex-wrap items-center justify-between gap-2 text-[11px] text-text-muted">
              <span>当前引擎：{{ metaInfo.active_engine || 'LocalEnterpriseChatModel' }}</span>
              <span>
                最近变更：{{ formattedUpdatedAt }}
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
  AlertCircle,
  CheckCircle2,
  X,
  Cpu,
  Zap,
  Sparkles,
  Check,
  KeyRound,
  Gauge,
  Database,
} from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import FuseButton from '../components/ui/FuseButton.vue';
import RubberSegment from '../components/ui/RubberSegment.vue';
import StatusMark from '../components/ui/StatusMark.vue';

const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(true);
const isSaving = ref(false);
const isProbing = ref(false);
const confirmReset = ref(false);
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
});

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
  { value: 'deep', label: '深度思考', icon: Sparkles },
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
  confirmReset.value = false;
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
