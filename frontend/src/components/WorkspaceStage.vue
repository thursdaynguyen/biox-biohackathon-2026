<script setup>
const props = defineProps({
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
  selectedCandidate: {
    type: Object,
    default: null,
  },
  selectedCandidateIndex: {
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
  'select-candidate',
  'update:top-k',
  'apply-candidate',
  'update-parameter',
  'evaluate',
])

function candidateMagnitude(candidate, key) {
  return Number(candidate?.parameters?.[key] ?? 0)
}

function maxMagnitudeForField(key) {
  const values = props.candidates.map((candidate) => candidateMagnitude(candidate, key))
  const maxValue = Math.max(...values, candidateMagnitude(props.bestCandidate, key), 0)
  return maxValue > 0 ? maxValue : 1
}

function fieldBarWidth(candidate, key) {
  const ratio = candidateMagnitude(candidate, key) / maxMagnitudeForField(key)
  return `${Math.max(12, ratio * 100)}%`
}

function candidateLabel(index) {
  return `Suggestion ${index + 1}`
}
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
        <article class="content-block wide-block">
          <div class="best-formulation-head">
            <div>
              <p class="section-kicker">Candidate formulation</p>
              <h4 class="section-heading">Composition overview</h4>
            </div>
            <span class="metric-badge">
              Cost {{ selectedCandidate ? formatDecimal(selectedCandidate.cost) : 'N/A' }}
            </span>
          </div>

          <div v-if="selectedCandidate" class="composition-grid">
            <TransitionGroup name="composition-swap" tag="div" class="composition-grid-inner">
              <div
                v-for="field in parameterFields"
                :key="`${selectedCandidate.id}-${field.key}`"
                class="composition-card"
              >
                <div class="composition-card-head">
                  <strong>{{ field.label }}</strong>
                  <span>{{ formatDecimal(selectedCandidate.parameters?.[field.key]) }}</span>
                </div>
                <div class="composition-track">
                  <div
                    class="composition-fill"
                    :style="{ width: fieldBarWidth(selectedCandidate, field.key) }"
                  ></div>
                </div>
              </div>
            </TransitionGroup>
          </div>
          <p v-else class="empty-copy">
            No optimization suggestions are available for the selected profile.
          </p>
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
          <p class="section-kicker">Candidate selector</p>
          <div v-if="candidates.length" class="candidate-selector">
            <button
              v-for="(candidate, index) in candidates"
              :key="`${index}-${candidate.cost}`"
              class="candidate-tab"
              :class="{ active: selectedCandidateIndex === index }"
              @click="$emit('select-candidate', index)"
            >
              <strong>{{ candidateLabel(index) }}</strong>
              <span>{{ formatDecimal(candidate.cost) }}</span>
            </button>
          </div>
          <div v-if="selectedCandidate" class="selector-actions">
            <button class="secondary-button" @click="$emit('apply-candidate', selectedCandidate)">
              Send this formulation to simulation
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
