<script setup>
defineProps({
  uploadStatus: {
    type: String,
    required: true,
  },
  uploadMessage: {
    type: String,
    required: true,
  },
  sessionId: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <header class="hero">
    <div class="hero-copy">
      <p class="eyebrow">MediaOpt Workspace</p>
      <h1>Genome-to-media optimization, designed for experimental teams.</h1>
      <p class="hero-text">
        Build a model session, compare recommended conditions, and evaluate your own
        parameter sets without working directly with GEM internals.
      </p>
    </div>

    <div class="hero-card panel">
      <p class="panel-label">Current session</p>
      <h2>{{ uploadStatus }}</h2>
      <p class="supporting-copy">{{ uploadMessage }}</p>
      <p class="session-token">{{ sessionId || 'Session pending' }}</p>
    </div>
  </header>
</template>
