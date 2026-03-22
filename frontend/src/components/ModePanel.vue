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
  topK: {
    type: Number,
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
})

defineEmits(['update:mode', 'update:top-k', 'fetch-optimum', 'fetch-candidates'])
</script>

<template>
  <section class="panel mode-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Step 2</p>
        <h2>Choose a workflow</h2>
      </div>
    </div>

    <div class="mode-switcher">
      <button
        class="mode-card"
        :class="{ active: mode === 'recommended' }"
        @click="$emit('update:mode', 'recommended')"
      >
        <strong>Recommended setup</strong>
        <span>Fetch the best point and compare top candidate conditions.</span>
      </button>

      <button
        class="mode-card"
        :class="{ active: mode === 'manual' }"
        @click="$emit('update:mode', 'manual')"
      >
        <strong>Manual evaluation</strong>
        <span>Enter your own values and inspect the resulting score and fluxes.</span>
      </button>
    </div>

    <p v-if="!sessionReady" class="empty-copy">
      Start a session first. Recommended optimization becomes available after upload.
    </p>

    <div class="inline-controls">
      <button
        class="secondary-button"
        :disabled="loadingOptimum || !sessionReady"
        @click="$emit('fetch-optimum')"
      >
        {{ loadingOptimum ? 'Loading optimum...' : 'Get optimum' }}
      </button>

      <label class="objective-field compact">
        <span>Top-k</span>
        <input
          :value="topK"
          type="number"
          min="1"
          max="20"
          @input="$emit('update:top-k', Number($event.target.value))"
        />
      </label>

      <button
        class="secondary-button"
        :disabled="loadingCandidates || !sessionReady"
        @click="$emit('fetch-candidates')"
      >
        {{ loadingCandidates ? 'Loading candidates...' : 'Get candidates' }}
      </button>
    </div>
  </section>
</template>
