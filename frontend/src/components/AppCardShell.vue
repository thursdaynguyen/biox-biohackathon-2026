<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    required: true,
  },
  sessionId: {
    type: String,
    default: '',
  },
  canGoBack: {
    type: Boolean,
    default: false,
  },
  canGoNext: {
    type: Boolean,
    default: false,
  },
  nextLabel: {
    type: String,
    default: 'Next step',
  },
})

defineEmits(['back', 'next'])
</script>

<template>
  <main class="card-shell">
    <header class="card-head">
      <div class="card-copy">
        <h2>{{ title }}</h2>
        <p class="card-description">{{ description }}</p>
      </div>

      <div class="card-status">
        <slot name="status" />
      </div>
    </header>

    <section class="card-body">
      <slot name="body" />
    </section>

    <footer class="card-foot">
      <div class="card-foot-slot left">
        <slot name="footer-left" />
      </div>
      <div class="card-foot-slot center">
        <slot name="footer-center" />
      </div>
      <div class="card-foot-slot right">
        <slot name="footer-right" />
      </div>
    </footer>
  </main>
</template>
