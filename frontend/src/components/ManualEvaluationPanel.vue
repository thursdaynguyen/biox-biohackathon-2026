<script setup>
defineProps({
  sessionReady: {
    type: Boolean,
    default: false,
  },
  parameterFields: {
    type: Array,
    required: true,
  },
  parameters: {
    type: Object,
    required: true,
  },
  loadingEvaluation: {
    type: Boolean,
    default: false,
  },
})

defineEmits(['update-parameter', 'evaluate'])
</script>

<template>
  <section class="panel manual-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Step 4</p>
        <h2>Manual evaluation</h2>
      </div>
    </div>

    <p v-if="!sessionReady" class="empty-copy">
      Create a workspace session before running a manual evaluation.
    </p>

    <div class="manual-form-grid">
      <label v-for="field in parameterFields" :key="field.key" class="slider-card">
        <div class="slider-head">
          <div>
            <strong>{{ field.label }}</strong>
            <small>{{ field.hint }}</small>
          </div>
          <span>{{ parameters[field.key] }}</span>
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

    <div class="inline-controls">
      <button
        class="primary-button"
        :disabled="loadingEvaluation || !sessionReady"
        @click="$emit('evaluate')"
      >
        {{ loadingEvaluation ? 'Evaluating...' : 'Run evaluation' }}
      </button>
    </div>
  </section>
</template>
