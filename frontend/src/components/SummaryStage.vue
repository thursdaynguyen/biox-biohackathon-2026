<script setup>
defineProps({
  bestCandidate: {
    type: Object,
    default: null,
  },
  evaluation: {
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
  summaryNarrative: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <div class="stage-layout summary-stage">
    <div class="summary-hero">
      <p class="section-kicker">Current takeaway</p>
      <h3>{{ summaryNarrative }}</h3>
    </div>

    <div class="summary-grid">
      <article class="content-block">
        <p class="section-kicker">Recommended signal</p>
        <h4>{{ bestCandidate?.score ?? 'Pending' }}</h4>
        <div class="chip-list">
          <span
            v-for="field in parameterFields"
            :key="field.key"
            class="mini-chip"
          >
            {{ field.label }}: {{ bestCandidate?.parameters?.[field.key] ?? 'N/A' }}
          </span>
        </div>
      </article>

      <article class="content-block">
        <p class="section-kicker">Manual result</p>
        <h4>{{ evaluation?.objective_value ?? 'Pending' }}</h4>
        <p class="section-copy">
          Objective: {{ evaluation?.target_objective || targetObjective }}
        </p>
      </article>
    </div>
  </div>
</template>
