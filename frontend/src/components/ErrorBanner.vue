<script setup>
defineProps({
  message: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <section class="error-banner">
    <strong>Request error</strong>
    <span>{{ message }}</span>
  </section>
</template>
