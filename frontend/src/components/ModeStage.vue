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
})

defineEmits(['update:mode', 'choose'])
</script>

<template>
  <div class="stage-layout mode-stage">
    <div class="mode-grid">
      <button
        class="mode-option"
        :class="{ active: mode === 'recommended' }"
        :disabled="!sessionReady"
        @click="$emit('update:mode', 'recommended')"
      >
        <p class="section-kicker">Optimization path</p>
        <h3>Get optimization suggestions</h3>
        <span>
          See the best recommended media settings and compare top candidate conditions
          from the optimization results.
        </span>
      </button>

      <button
        class="mode-option"
        :class="{ active: mode === 'manual' }"
        :disabled="!sessionReady"
        @click="$emit('update:mode', 'manual')"
      >
        <p class="section-kicker">Simulation path</p>
        <h3>Simulate a parameter set</h3>
        <span>
          Enter your own media parameters and run a live simulation to inspect the
          resulting model behavior.
        </span>
      </button>
    </div>
  </div>
</template>
