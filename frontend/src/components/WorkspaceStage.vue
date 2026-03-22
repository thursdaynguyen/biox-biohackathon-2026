<script setup>
defineProps({
  mode: {
    type: String,
    required: true,
  },
  sessionReady: {
    type: Boolean,
    default: false,
  },
  targetObjective: {
    type: String,
    required: true,
  },
  topK: {
    type: Number,
    required: true,
  },
  bestCandidate: {
    type: Object,
    default: null,
  },
  candidates: {
    type: Array,
    required: true,
  },
  candidateMaxScore: {
    type: Number,
    required: true,
  },
  evaluation: {
    type: Object,
    default: null,
  },
  diagnostics: {
    type: Array,
    required: true,
  },
  parameters: {
    type: Object,
    required: true,
  },
  parameterFields: {
    type: Array,
    required: true,
  },
  loadingOptimum: {
    type: Boolean,
    default: false,
  },
  loadingCandidates: {
    type: Boolean,
    default: false,
  },
  loadingEvaluation: {
    type: Boolean,
    default: false,
  },
  modeDirection: {
    type: String,
    required: true,
  },
})

defineEmits([
  'switch-mode',
  'update:top-k',
  'fetch-optimum',
  'fetch-candidates',
  'apply-candidate',
  'update-parameter',
  'evaluate',
])
</script>

<template>
  <div class="stage-layout workspace-stage">
    <div class="workspace-topbar">
      <div class="mode-toggle">
        <button
          class="toggle-chip"
          :class="{ active: mode === 'recommended' }"
          @click="$emit('switch-mode', 'recommended')"
        >
          Recommended
        </button>
        <button
          class="toggle-chip"
          :class="{ active: mode === 'manual' }"
          @click="$emit('switch-mode', 'manual')"
        >
          Manual
        </button>
      </div>
      <span class="meta-note">{{ targetObjective }} objective</span>
    </div>

    <div class="workspace-viewport">
      <div
        class="workspace-track"
        :class="{
          recommended: modeDirection === 'recommended',
          manual: modeDirection === 'manual',
        }"
      >
        <section class="workspace-panel recommended-panel">
          <div class="workspace-grid">
            <article class="content-block emphasis-block">
              <p class="section-kicker">Best available point</p>
              <h3>
                {{ bestCandidate?.score ?? 'No score yet' }}
              </h3>
              <p class="section-copy">
                {{ bestCandidate ? 'Use this as the strongest available starting point.' : 'Fetch the optimum to populate the strongest signal.' }}
              </p>
            </article>

            <article class="content-block compact-block">
              <div class="mini-actions">
                <button
                  class="secondary-button"
                  :disabled="loadingOptimum || !sessionReady"
                  @click="$emit('fetch-optimum')"
                >
                  {{ loadingOptimum ? 'Loading optimum...' : 'Fetch optimum' }}
                </button>

                <div class="inline-field">
                  <label for="top-k-input">Top-k</label>
                  <input
                    id="top-k-input"
                    :value="topK"
                    type="number"
                    min="1"
                    max="20"
                    @input="$emit('update:top-k', Number($event.target.value))"
                  />
                </div>

                <button
                  class="secondary-button"
                  :disabled="loadingCandidates || !sessionReady"
                  @click="$emit('fetch-candidates')"
                >
                  {{ loadingCandidates ? 'Loading candidates...' : 'Fetch candidates' }}
                </button>
              </div>
            </article>

            <article class="content-block wide-block">
              <p class="section-kicker">Top candidate comparison</p>
              <div v-if="candidates.length" class="candidate-list">
                <button
                  v-for="(candidate, index) in candidates"
                  :key="`${index}-${candidate.score}`"
                  class="candidate-item"
                  @click="$emit('apply-candidate', candidate)"
                >
                  <div class="candidate-copy">
                    <strong>Candidate {{ index + 1 }}</strong>
                    <span>{{ candidate.score ?? 'N/A' }}</span>
                  </div>
                  <div class="candidate-bar">
                    <div
                      class="candidate-fill"
                      :style="{ width: `${((candidate.score ?? 0) / candidateMaxScore) * 100}%` }"
                    ></div>
                  </div>
                </button>
              </div>
              <p v-else class="empty-copy">
                Candidate results will appear here after the search request completes.
              </p>
            </article>
          </div>
        </section>

        <section class="workspace-panel manual-panel">
          <div class="workspace-grid">
            <article class="content-block wide-block">
              <p class="section-kicker">Manual controls</p>
              <div class="slider-grid">
                <label
                  v-for="field in parameterFields"
                  :key="field.key"
                  class="slider-field"
                >
                  <div class="slider-head">
                    <div>
                      <strong>{{ field.label }}</strong>
                      <span>{{ field.hint }}</span>
                    </div>
                    <small>{{ parameters[field.key] }}</small>
                  </div>
                  <input
                    :value="parameters[field.key]"
                    type="range"
                    :min="field.min"
                    :max="field.max"
                    :step="field.step"
                    :disabled="!sessionReady"
                    @input="$emit('update-parameter', { key: field.key, value: Number($event.target.value) })"
                  />
                </label>
              </div>

              <div class="manual-actions">
                <button
                  class="primary-button"
                  :disabled="loadingEvaluation || !sessionReady"
                  @click="$emit('evaluate')"
                >
                  {{ loadingEvaluation ? 'Evaluating...' : 'Run evaluation' }}
                </button>
              </div>
            </article>

            <article class="content-block compact-block">
              <p class="section-kicker">Current result</p>
              <h3>{{ evaluation?.objective_value ?? 'No result yet' }}</h3>
              <p class="section-copy">
                {{ evaluation ? 'Inspect the flux snapshot below and compare it with the recommended signal.' : 'Run a manual evaluation to inspect objective values and diagnostics.' }}
              </p>
            </article>

            <article class="content-block wide-block">
              <p class="section-kicker">Diagnostics and flux snapshot</p>
              <div v-if="evaluation" class="diagnostic-grid">
                <div
                  v-for="(value, key) in evaluation.fluxes"
                  :key="key"
                  class="diagnostic-card"
                >
                  <span>{{ key }}</span>
                  <strong>{{ value }}</strong>
                </div>
                <div
                  v-for="[key, value] in diagnostics"
                  :key="key"
                  class="diagnostic-card subtle"
                >
                  <span>{{ key }}</span>
                  <strong>{{ value }}</strong>
                </div>
              </div>
              <p v-else class="empty-copy">
                The manual diagnostics area will populate after evaluation.
              </p>
            </article>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>
