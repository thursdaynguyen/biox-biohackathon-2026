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
  profileOptions: {
    type: Array,
    required: true,
  },
  selectedProfile: {
    type: String,
    default: '',
  },
})

defineEmits(['file-change', 'update:selected-profile'])
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

    <label class="field-block profile-field">
      <span>Demo profile</span>
      <select
        :value="selectedProfile"
        @change="$emit('update:selected-profile', $event.target.value)"
      >
        <option disabled value="">Select a profile</option>
        <option v-for="option in profileOptions" :key="option" :value="option">
          {{ option }}
        </option>
      </select>
    </label>

    <label class="upload-dropzone">
      <input type="file" accept=".faa,.fa,.fasta" @change="$emit('file-change', $event)" />
      <strong>{{ uploadFileName || 'Choose a .faa, .fa, or .fasta file' }}</strong>
      <span>
        Preferred demo input: annotated protein FASTA matched to the selected demo profile.
      </span>

      <div v-if="uploadLoading" class="upload-overlay">
        <p class="section-kicker">Preparing workspace</p>
        <p class="loading-copy">Building your demo workspace...</p>
        <div class="loading-meter" aria-hidden="true">
          <span></span>
        </div>
      </div>
    </label>
  </div>
</template>
