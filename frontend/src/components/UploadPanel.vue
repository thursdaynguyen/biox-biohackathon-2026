<script setup>
defineProps({
  sessionId: {
    type: String,
    default: '',
  },
  uploadFileName: {
    type: String,
    default: '',
  },
  uploadLoading: {
    type: Boolean,
    default: false,
  },
  targetObjective: {
    type: String,
    required: true,
  },
})

defineEmits(['file-change', 'upload', 'update:target-objective'])
</script>

<template>
  <section class="panel upload-panel">
    <div class="panel-header">
      <div>
        <p class="panel-label">Step 1</p>
        <h2>Create a workspace session</h2>
      </div>
      <span class="status-pill" :class="{ ready: sessionId }">
        {{ sessionId ? 'Ready' : 'Waiting' }}
      </span>
    </div>

    <p class="supporting-copy">
      This pipeline can support genome- and protein-derived model building. For the current
      demo, we use a CarveMe workflow with protein FASTA input for the most reliable run.
    </p>

    <label class="upload-dropzone">
      <input type="file" accept=".faa,.fa,.fasta" @change="$emit('file-change', $event)" />
      <span>{{ uploadFileName || 'Drop a protein FASTA file here (.faa preferred)' }}</span>
      <small>
        Demo input: protein FASTA. Broader genome-oriented preprocessing can be added later.
      </small>
    </label>

    <div class="inline-controls">
      <button class="primary-button" :disabled="uploadLoading" @click="$emit('upload')">
        {{ uploadLoading ? 'Creating session...' : 'Start session' }}
      </button>

      <label class="objective-field">
        <span>Objective</span>
        <select
          :value="targetObjective"
          @change="$emit('update:target-objective', $event.target.value)"
        >
          <option value="growth">Growth</option>
          <option value="product">Product</option>
        </select>
      </label>
    </div>
  </section>
</template>
