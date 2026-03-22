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
  'apply-candidate',
  'update-parameter',
  'evaluate',
])

const BAR_MIN = -15
const BAR_MAX = 15
const BAR_RANGE = BAR_MAX - BAR_MIN

function candidateMagnitude(candidate, key) {
  return Number(candidate?.parameters?.[key] ?? 0)
}

function fieldBarStyle(candidate, key) {
  const value = candidateMagnitude(candidate, key)
  const clampedValue = Math.min(BAR_MAX, Math.max(BAR_MIN, value))
  const width = ((clampedValue - BAR_MIN) / BAR_RANGE) * 100

  return {
    width: `${width}%`,
  }
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
            <div class="best-formulation-controls">
              <div v-if="candidates.length" class="candidate-navigator">
                <button
                  class="nav-arrow"
                  :disabled="selectedCandidateIndex <= 0"
                  @click="$emit('select-candidate', selectedCandidateIndex - 1)"
                >
                  Previous
                </button>
                <div class="candidate-readout">
                  <strong>{{ candidateLabel(selectedCandidateIndex) }}</strong>
                  <span>{{ selectedCandidateIndex + 1 }} / {{ candidates.length }}</span>
                </div>
                <button
                  class="nav-arrow"
                  :disabled="selectedCandidateIndex >= candidates.length - 1"
                  @click="$emit('select-candidate', selectedCandidateIndex + 1)"
                >
                  Next
                </button>
              </div>
              <span class="metric-badge">
                Cost {{ selectedCandidate ? formatDecimal(selectedCandidate.cost) : 'N/A' }}
              </span>
            </div>
          </div>

          <div v-if="selectedCandidate" class="composition-grid">
            <div class="composition-grid-inner">
              <div
                v-for="field in parameterFields"
                :key="field.key"
                class="composition-card"
              >
                <div class="composition-card-head">
                  <strong>{{ field.label }}</strong>
                  <span>{{ formatDecimal(selectedCandidate.parameters?.[field.key]) }}</span>
                </div>
                <div class="composition-track">
                  <div
                    class="composition-fill"
                    :style="fieldBarStyle(selectedCandidate, field.key)"
                  ></div>
                </div>
              </div>
            </div>
          </div>
          <p v-else class="empty-copy">
            No optimization suggestions are available for the selected profile.
          </p>
        </article>

        <div v-if="selectedCandidate" class="workspace-inline-actions">
          <button class="secondary-button" @click="$emit('apply-candidate', selectedCandidate)">
            Send this formulation to simulation
          </button>
        </div>
      </div>
    </div>

    <div v-else class="workspace-page">
      <div class="workspace-page-head">
        <div>
          <p class="section-kicker">Parameter simulation</p>
          <h3>Simulation setup</h3>
        </div>
        <button class="ghost-button subtle-switch" @click="$emit('switch-mode', 'recommended')">
          Switch to optimization suggestions
        </button>
      </div>

      <div class="workspace-grid">
        <article class="content-block wide-block">
          <div class="best-formulation-head">
            <div>
              <p class="section-kicker">Parameter set</p>
              <h4 class="section-heading">Simulation setup</h4>
            </div>
            <span class="metric-badge">
              Result {{ evaluation ? formatDecimal(evaluation.objective_value) : 'No result yet' }}
            </span>
          </div>

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

          <div class="workspace-inline-actions">
            <button
              class="primary-button"
              :disabled="loadingEvaluation || !sessionReady"
              @click="$emit('evaluate')"
            >
              {{ loadingEvaluation ? 'Running simulation...' : 'Run simulation' }}
            </button>
          </div>
        </article>

        <article class="content-block wide-block">
          <p class="section-kicker">Simulation details</p>
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
