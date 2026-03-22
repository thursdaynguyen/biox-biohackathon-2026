<script setup>
defineProps({
  bestCandidate: {
    type: Object,
    default: null,
  },
  parameterFields: {
    type: Array,
    required: true,
  },
  targetObjective: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <section class="panel summary-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Step 3</p>
        <h2>Best available signal</h2>
      </div>
    </div>

    <div v-if="bestCandidate" class="summary-stack">
      <div class="metric-row">
        <div>
          <span class="metric-label">Best score</span>
          <strong class="metric-value">
            {{ bestCandidate.score ?? 'Pending core result' }}
          </strong>
        </div>
        <div>
          <span class="metric-label">Objective</span>
          <strong class="metric-value subtle">{{ targetObjective }}</strong>
        </div>
      </div>

      <div class="parameter-chip-grid">
        <span
          v-for="field in parameterFields"
          :key="field.key"
          class="parameter-chip"
        >
          {{ field.label }}:
          {{ bestCandidate.parameters?.[field.key] ?? 'N/A' }}
        </span>
      </div>
    </div>
    <p v-else class="empty-copy">
      Run the recommended workflow to populate the best candidate summary.
    </p>
  </section>
</template>
