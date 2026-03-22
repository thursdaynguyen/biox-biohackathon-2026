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
  mockAccession: {
    type: String,
    default: '',
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
  formatDecimal: {
    type: Function,
    required: true,
  },
  loadingEvaluation: {
    type: Boolean,
    default: false,
  },
})

defineEmits([
  'switch-mode',
  'update:top-k',
  'apply-candidate',
  'update-parameter',
  'evaluate',
])
</script>

<template>
  <div class="stage-layout workspace-stage">
    <div v-if="mode === 'recommended'" class="workspace-page">
      <div class="workspace-page-head">
        <div>
          <p class="section-kicker">Optimization suggestions</p>
          <h3>Suggested conditions</h3>
        </div>
        <button class="ghost-button subtle-switch" @click="$emit('switch-mode', 'manual')">
          Switch to parameter simulation
        </button>
      </div>

      <div class="workspace-grid">
        <article class="content-block emphasis-block">
          <p class="section-kicker">Suggested best condition</p>
          <h3>{{ bestCandidate ? formatDecimal(bestCandidate.cost) : 'No cost yet' }}</h3>
        </article>

        <article class="content-block compact-block">
          <div class="inline-field">
            <label for="top-k-input">Show top candidates</label>
            <input
              id="top-k-input"
              :value="topK"
              type="number"
              min="1"
              max="20"
              @input="$emit('update:top-k', Number($event.target.value))"
            />
          </div>
        </article>

        <article class="content-block wide-block">
          <p class="section-kicker">Top suggested conditions</p>
          <div v-if="candidates.length" class="candidate-list">
            <button
              v-for="(candidate, index) in candidates"
              :key="`${index}-${candidate.cost}`"
              class="candidate-item"
              @click="$emit('apply-candidate', candidate)"
            >
              <div class="candidate-copy">
                <strong>Suggestion {{ index + 1 }}</strong>
                <span>Cost {{ formatDecimal(candidate.cost) }}</span>
              </div>
              <div class="candidate-bar">
                <div
                  class="candidate-fill"
                  :style="{ width: candidate.barWidth || '35%' }"
                ></div>
              </div>
            </button>
          </div>
          <p v-else class="empty-copy">
            No optimization suggestions are available for the selected profile.
          </p>
        </article>
      </div>
    </div>

    <div v-else class="workspace-page">
      <div class="workspace-page-head">
        <div>
          <p class="section-kicker">Parameter simulation</p>
          <h3>Simulate a custom parameter set</h3>
        </div>
        <button class="ghost-button subtle-switch" @click="$emit('switch-mode', 'recommended')">
          Switch to optimization suggestions
        </button>
      </div>

      <div class="workspace-grid">
        <article class="content-block wide-block">
          <p class="section-kicker">Parameter set</p>
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
                <small>{{ formatDecimal(parameters[field.key]) }}</small>
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
              {{ loadingEvaluation ? 'Running simulation...' : 'Run simulation' }}
            </button>
          </div>
        </article>

        <article class="content-block compact-block">
          <p class="section-kicker">Simulation result</p>
          <h3>{{ evaluation ? formatDecimal(evaluation.objective_value) : 'No result yet' }}</h3>
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
              <strong>{{ formatDecimal(value) }}</strong>
            </div>
            <div
              v-for="[key, value] in diagnostics"
              :key="key"
              class="diagnostic-card subtle"
            >
              <span>{{ key }}</span>
              <strong>{{ formatDecimal(value) }}</strong>
            </div>
          </div>
          <p v-else class="empty-copy">
            The simulation diagnostics area will populate after you run the model.
          </p>
        </article>
      </div>
    </div>
  </div>
</template>
