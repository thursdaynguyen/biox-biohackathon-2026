<script setup>
defineProps({
  candidates: {
    type: Array,
    required: true,
  },
  candidateMaxScore: {
    type: Number,
    required: true,
  },
})

defineEmits(['apply-candidate'])
</script>

<template>
  <section class="panel candidates-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Visualization</p>
        <h2>Top candidate comparison</h2>
      </div>
    </div>

    <div v-if="candidates.length" class="candidate-bars">
      <button
        v-for="(candidate, index) in candidates"
        :key="`${index}-${candidate.score}`"
        class="candidate-bar-card"
        @click="$emit('apply-candidate', candidate)"
      >
        <div class="candidate-bar-meta">
          <span>Candidate {{ index + 1 }}</span>
          <strong>{{ candidate.score ?? 'N/A' }}</strong>
        </div>
        <div class="bar-track">
          <div
            class="bar-fill"
            :style="{
              width: `${((candidate.score ?? 0) / candidateMaxScore) * 100}%`,
            }"
          ></div>
        </div>
        <small>Click to load these parameters into manual evaluation.</small>
      </button>
    </div>
    <p v-else class="empty-copy">
      Candidate comparison will appear here after the top-k request completes.
    </p>
  </section>
</template>
