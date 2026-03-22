<script setup>
defineProps({
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
  <div class="stage-layout upload-stage">
    <div class="content-block lead-block">
      <p class="section-kicker">Working input</p>
      <h3>Upload a protein FASTA file</h3>
      <p class="section-copy">
        The broader pipeline can support genome-oriented workflows, but this demo uses a
        CarveMe + protein FASTA path for a more reliable live run.
      </p>
    </div>

    <label class="upload-dropzone">
      <input type="file" accept=".faa,.fa,.fasta" @change="$emit('file-change', $event)" />
      <strong>{{ uploadFileName || 'Choose a .faa, .fa, or .fasta file' }}</strong>
      <span>Preferred demo input: annotated protein FASTA.</span>
    </label>

    <div class="stage-row">
      <label class="field-block">
        <span>Objective</span>
        <select
          :value="targetObjective"
          @change="$emit('update:target-objective', $event.target.value)"
        >
          <option value="growth">Growth</option>
          <option value="product">Product</option>
        </select>
      </label>

      <button class="primary-button" :disabled="uploadLoading" @click="$emit('upload')">
        {{ uploadLoading ? 'Creating session...' : 'Start session' }}
      </button>
    </div>
  </div>
</template>
