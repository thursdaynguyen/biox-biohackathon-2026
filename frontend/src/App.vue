<script setup>
import { computed, reactive, ref } from 'vue'
import CandidatesPanel from './components/CandidatesPanel.vue'
import DiagnosticsPanel from './components/DiagnosticsPanel.vue'
import ErrorBanner from './components/ErrorBanner.vue'
import HeroSection from './components/HeroSection.vue'
import ManualEvaluationPanel from './components/ManualEvaluationPanel.vue'
import ModePanel from './components/ModePanel.vue'
import SummaryPanel from './components/SummaryPanel.vue'
import UploadPanel from './components/UploadPanel.vue'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''
const ALLOWED_UPLOAD_SUFFIXES = ['.faa', '.fa', '.fasta']

const targetObjective = ref('growth')
const mode = ref('recommended')
const sessionId = ref('')
const uploadFile = ref(null)
const uploadStatus = ref('No model session yet')
const uploadMessage = ref('Use protein FASTA input for the current CarveMe-based demo session.')
const uploadLoading = ref(false)

const optimum = ref(null)
const candidates = ref([])
const evaluation = ref(null)
const loading = reactive({
  optimum: false,
  candidates: false,
  evaluation: false,
})

const errorMessage = ref('')

const parameterFields = [
  { key: 'EX_glc__D_e', label: 'Glucose', hint: 'Primary carbon source', min: 0, max: 20, step: 0.5 },
  { key: 'EX_nh4_e', label: 'Ammonium', hint: 'Primary nitrogen source', min: 0, max: 10, step: 0.5 },
  { key: 'EX_pi_e', label: 'Phosphate', hint: 'Phosphorus availability', min: 0, max: 10, step: 0.5 },
  { key: 'EX_so4_e', label: 'Sulfate', hint: 'Sulfur availability', min: 0, max: 10, step: 0.5 },
  { key: 'EX_o2_e', label: 'Oxygen', hint: 'Aeration proxy', min: 0, max: 100, step: 5 },
]

const parameters = reactive(
  parameterFields.reduce((accumulator, field) => {
    accumulator[field.key] = field.key === 'EX_o2_e' ? 20 : field.key === 'EX_glc__D_e' ? 10 : 5
    return accumulator
  }, {}),
)

const topK = ref(5)

const candidateMaxScore = computed(() => {
  if (!candidates.value.length) return 1
  return Math.max(...candidates.value.map((candidate) => candidate.score ?? 0), 1)
})

const formattedEvaluationDiagnostics = computed(() => {
  if (!evaluation.value?.diagnostics) return []
  return Object.entries(evaluation.value.diagnostics)
})

const bestCandidatePreview = computed(() => {
  if (optimum.value) return optimum.value
  if (candidates.value.length) return candidates.value[0]
  return null
})

function onFileChange(event) {
  const [file] = event.target.files ?? []
  if (!file) {
    uploadFile.value = null
    return
  }

  const lowerName = file.name.toLowerCase()
  const isAllowed = ALLOWED_UPLOAD_SUFFIXES.some((suffix) => lowerName.endsWith(suffix))

  if (!isAllowed) {
    uploadFile.value = null
    errorMessage.value =
      'Unsupported file type. Please upload a protein FASTA file (.faa, .fa, or .fasta).'
    event.target.value = ''
    return
  }

  clearError()
  uploadFile.value = file
}

function updateMode(nextMode) {
  mode.value = nextMode
}

function updateTargetObjective(nextObjective) {
  targetObjective.value = nextObjective
}

function updateTopK(nextValue) {
  topK.value = Math.min(Math.max(Number(nextValue) || 1, 1), 20)
}

function updateParameter({ key, value }) {
  parameters[key] = value
}

function applyCandidate(candidate) {
  for (const field of parameterFields) {
    if (candidate.parameters[field.key] != null) {
      parameters[field.key] = candidate.parameters[field.key]
    }
  }
  mode.value = 'manual'
}

function clearError() {
  errorMessage.value = ''
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message =
      data?.error?.message ??
      data?.detail ??
      `Request failed with status ${response.status}.`
    throw new Error(message)
  }

  return data
}

async function handleUpload() {
  clearError()
  if (!uploadFile.value) {
    errorMessage.value = 'Choose a file before starting a workspace session.'
    return
  }

  uploadLoading.value = true
  try {
    const formData = new FormData()
    formData.append('file', uploadFile.value)
    const data = await apiRequest('/api/upload', {
      method: 'POST',
      body: formData,
    })

    sessionId.value = data.session_id
    uploadStatus.value = 'Session ready'
    uploadMessage.value = `Model session created for ${uploadFile.value.name}.`
    optimum.value = null
    candidates.value = []
    evaluation.value = null
  } catch (error) {
    errorMessage.value = error.message
    uploadStatus.value = 'Upload failed'
  } finally {
    uploadLoading.value = false
  }
}

async function fetchOptimum() {
  if (!sessionId.value) {
    errorMessage.value = 'Create a session before requesting optimized conditions.'
    return
  }

  clearError()
  loading.optimum = true
  try {
    const data = await apiRequest('/api/optimum', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        target_objective: targetObjective.value,
      }),
    })
    optimum.value = data.optimum
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.optimum = false
  }
}

async function fetchCandidates() {
  if (!sessionId.value) {
    errorMessage.value = 'Create a session before requesting candidate conditions.'
    return
  }

  clearError()
  loading.candidates = true
  try {
    const data = await apiRequest('/api/candidates', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        top_k: topK.value,
        target_objective: targetObjective.value,
      }),
    })
    candidates.value = data.candidates ?? []
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.candidates = false
  }
}

async function handleEvaluate() {
  if (!sessionId.value) {
    errorMessage.value = 'Create a session before running a manual evaluation.'
    return
  }

  clearError()
  loading.evaluation = true
  try {
    evaluation.value = await apiRequest('/api/evaluate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        parameters: Object.fromEntries(
          Object.entries(parameters).map(([key, value]) => [key, Number(value)]),
        ),
        target_objective: targetObjective.value,
      }),
    })
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    loading.evaluation = false
  }
}
</script>

<template>
  <div class="app-shell">
    <div class="background-ornament background-ornament-left"></div>
    <div class="background-ornament background-ornament-right"></div>

    <HeroSection
      :upload-status="uploadStatus"
      :upload-message="uploadMessage"
      :session-id="sessionId"
    />

    <ErrorBanner v-if="errorMessage" :message="errorMessage" />

    <main class="workspace-grid">
      <UploadPanel
        :session-id="sessionId"
        :upload-file-name="uploadFile?.name || ''"
        :upload-loading="uploadLoading"
        :target-objective="targetObjective"
        @file-change="onFileChange"
        @upload="handleUpload"
        @update:target-objective="updateTargetObjective"
      />

      <ModePanel
        :mode="mode"
        :session-ready="Boolean(sessionId)"
        :top-k="topK"
        :loading-optimum="loading.optimum"
        :loading-candidates="loading.candidates"
        @update:mode="updateMode"
        @update:top-k="updateTopK"
        @fetch-optimum="fetchOptimum"
        @fetch-candidates="fetchCandidates"
      />

      <SummaryPanel
        :best-candidate="bestCandidatePreview"
        :parameter-fields="parameterFields"
        :target-objective="targetObjective"
      />

      <CandidatesPanel
        :candidates="candidates"
        :candidate-max-score="candidateMaxScore"
        @apply-candidate="applyCandidate"
      />

      <ManualEvaluationPanel
        :session-ready="Boolean(sessionId)"
        :parameter-fields="parameterFields"
        :parameters="parameters"
        :loading-evaluation="loading.evaluation"
        @update-parameter="updateParameter"
        @evaluate="handleEvaluate"
      />

      <DiagnosticsPanel
        :evaluation="evaluation"
        :diagnostics="formattedEvaluationDiagnostics"
      />
    </main>
  </div>
</template>
