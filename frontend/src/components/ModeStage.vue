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
    <p v-if="!sessionReady" class="empty-copy">
      Start a session first. The workspace will unlock after upload.
    </p>

    <div class="mode-grid">
      <button
        class="mode-option"
        :class="{ active: mode === 'recommended' }"
        :disabled="!sessionReady"
        @click="$emit('update:mode', 'recommended')"
      >
        <p class="section-kicker">Recommended</p>
        <h3>Let the workflow propose strong candidates</h3>
        <span>Fetch the best point first, then compare the top candidates.</span>
      </button>

      <button
        class="mode-option"
        :class="{ active: mode === 'manual' }"
        :disabled="!sessionReady"
        @click="$emit('update:mode', 'manual')"
      >
        <p class="section-kicker">Manual</p>
        <h3>Test your own media parameters</h3>
        <span>Set a small number of key variables and inspect the resulting score.</span>
      </button>
    </div>

    <div class="mode-action-row">
      <button
        class="primary-button"
        :disabled="!sessionReady"
        @click="$emit('choose', mode)"
      >
        Enter {{ mode === 'recommended' ? 'recommended' : 'manual' }} workspace
      </button>
    </div>
  </div>
</template>
