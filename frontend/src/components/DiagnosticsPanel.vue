<script setup>
defineProps({
  evaluation: {
    type: Object,
    default: null,
  },
  diagnostics: {
    type: Array,
    required: true,
  },
})
</script>

<template>
  <section class="panel diagnostics-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Step 5</p>
        <h2>Diagnostics and flux snapshot</h2>
      </div>
    </div>

    <template v-if="evaluation">
      <div class="metric-row">
        <div>
          <span class="metric-label">Objective value</span>
          <strong class="metric-value">{{ evaluation.objective_value }}</strong>
        </div>
        <div>
          <span class="metric-label">Objective mode</span>
          <strong class="metric-value subtle">
            {{ evaluation.target_objective || 'default' }}
          </strong>
        </div>
      </div>

      <div class="flux-grid">
        <div
          v-for="(value, key) in evaluation.fluxes"
          :key="key"
          class="flux-card"
        >
          <span>{{ key }}</span>
          <strong>{{ value }}</strong>
        </div>
      </div>

      <div class="diagnostic-list">
        <div
          v-for="[key, value] in diagnostics"
          :key="key"
          class="diagnostic-item"
        >
          <span>{{ key }}</span>
          <strong>{{ value }}</strong>
        </div>
      </div>
    </template>
    <p v-else class="empty-copy">
      Run a manual evaluation to inspect objective values, fluxes, and diagnostics.
    </p>
  </section>
</template>
