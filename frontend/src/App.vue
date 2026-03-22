<script setup>
import { computed, reactive, ref } from 'vue'

import AppCardShell from './components/AppCardShell.vue'
import ModeStage from './components/ModeStage.vue'
import SummaryStage from './components/SummaryStage.vue'
import UploadStage from './components/UploadStage.vue'
import WorkspaceStage from './components/WorkspaceStage.vue'

const API_PREFIX = '/api'
const ALLOWED_UPLOAD_SUFFIXES = ['.faa', '.fa', '.fasta']

const parameterFields = [
  {
    key: 'EX_glc__D_e',
    label: 'Glucose uptake',
    hint: 'Primary carbon availability',
    min: 0,
    max: 25,
    step: 0.5,
  },
  {
    key: 'EX_nh4_e',
    label: 'Ammonium uptake',
    hint: 'Nitrogen supply',
    min: 0,
    max: 20,
    step: 0.5,
  },
  {
    key: 'EX_pi_e',
    label: 'Phosphate uptake',
    hint: 'Phosphorus balance',
    min: 0,
    max: 15,
    step: 0.5,
  },
  {
    key: 'EX_so4_e',
    label: 'Sulfate uptake',
    hint: 'Sulfur source',
    min: 0,
    max: 15,
    step: 0.5,
  },
  {
    key: 'EX_o2_e',
    label: 'Oxygen uptake',
    hint: 'Aeration window',
    min: 0,
    max: 30,
    step: 1,
  },
]

const stepTitles = [
  {
    eyebrow: 'Step 1 of 4',
    title: 'Create a model session',
    description: 'Start the demo with a protein FASTA file and set the objective you want to explore.',
  },
  {
    eyebrow: 'Step 2 of 4',
    title: 'Choose an exploration path',
    description: 'Pick the workflow you want to enter first. You can still switch inside the workspace.',
  },
  {
    eyebrow: 'Step 3 of 4',
    title: 'Explore candidate conditions',
    description: 'Move between recommended and manual exploration without leaving the same workspace.',
  },
  {
    eyebrow: 'Step 4 of 4',
    title: 'Review the strongest signal',
    description: 'Summarize what the model currently suggests and what to try next.',
  },
]

const currentStep = ref(0)
const stepDirection = ref('forward')
const activeMode = ref('recommended')
const targetObjective = ref('growth')
const uploadFile = ref(null)
const uploadFileName = ref('')
const sessionId = ref('')
const modelPath = ref('')
const errorMessage = ref('')

const loading = reactive({
  upload: false,
  optimum: false,
  candidates: false,
  evaluation: false,
})

const parameters = reactive({
  EX_glc__D_e: 10,
  EX_nh4_e: 5,
  EX_pi_e: 3,
  EX_so4_e: 2,
  EX_o2_e: 18,
})

const topK = ref(5)
const optimum = ref(null)
const candidates = ref([])
const evaluation = ref(null)

const sessionReady = computed(() => Boolean(sessionId.value))
const currentCopy = computed(() => stepTitles[currentStep.value])
const modeDirection = computed(() => (activeMode.value === 'recommended' ? 'recommended' : 'manual'))

const bestAvailableCandidate = computed(() => {
  if (optimum.value?.parameters) {
    return optimum.value
  }

  if (candidates.value.length > 0) {
    return candidates.value[0]
  }

  return null
})

const candidateMaxScore = computed(() => {
  const allScores = candidates.value
    .map((candidate) => Number(candidate.score ?? 0))
    .filter((score) => Number.isFinite(score) && score > 0)

  return allScores.length ? Math.max(...allScores) : 1
})

const diagnosticsEntries = computed(() => {
  if (!evaluation.value?.diagnostics) {
    return []
  }

  return Object.entries(evaluation.value.diagnostics)
})

const summaryNarrative = computed(() => {
  if (evaluation.value && bestAvailableCandidate.value) {
    const delta = Number(bestAvailableCandidate.value.score ?? 0) - Number(evaluation.value.objective_value ?? 0)

    if (delta > 0) {
      return 'The recommended condition currently performs better than the manual setup under the selected objective.'
    }

    return 'The manual setup is currently matching or outperforming the recommended signal in this demo run.'
  }

  if (bestAvailableCandidate.value) {
    return 'The strongest available recommendation comes from the automated search path.'
  }

  if (evaluation.value) {
    return 'A manual evaluation is available, but no recommended candidate has been fetched yet.'
  }

  return 'Run either recommended or manual exploration to generate an actionable summary.'
})

function resetError() {
  errorMessage.value = ''
}

function setError(message) {
  errorMessage.value = message || 'The request failed.'
}

function isAllowedFile(fileName) {
  const lowerName = fileName.toLowerCase()
  return ALLOWED_UPLOAD_SUFFIXES.some((suffix) => lowerName.endsWith(suffix))
}

function onFileChange(event) {
  resetError()
  const file = event.target.files?.[0]

  if (!file) {
    uploadFile.value = null
    uploadFileName.value = ''
    return
  }

  if (!isAllowedFile(file.name)) {
    uploadFile.value = null
    uploadFileName.value = ''
    event.target.value = ''
    setError('Unsupported file type. Please upload a protein FASTA file (.faa, .fa, or .fasta).')
    return
  }

  uploadFile.value = file
  uploadFileName.value = file.name
}

async function parseError(response) {
  try {
    const payload = await response.json()

    if (payload?.error?.message) {
      return payload.error.message
    }

    if (payload?.detail) {
      return typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)
    }
  } catch {
    return `Request failed with status ${response.status}.`
  }

  return `Request failed with status ${response.status}.`
}

async function uploadGenome() {
  resetError()

  if (!uploadFile.value) {
    setError('Select a protein FASTA file before starting the session.')
    return
  }

  const formData = new FormData()
  formData.append('file', uploadFile.value)

  loading.upload = true

  try {
    const response = await fetch(`${API_PREFIX}/upload`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(await parseError(response))
    }

    const payload = await response.json()
    sessionId.value = payload.session_id
    modelPath.value = payload.model_path
    currentStep.value = 1
  } catch (error) {
    setError(error instanceof Error ? error.message : 'The upload request failed.')
  } finally {
    loading.upload = false
  }
}

async function fetchOptimum() {
  resetError()

  if (!sessionReady.value) {
    setError('Create a session before requesting the recommended setup.')
    return
  }

  loading.optimum = true

  try {
    const response = await fetch(`${API_PREFIX}/optimum`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        target_objective: targetObjective.value,
      }),
    })

    if (!response.ok) {
      throw new Error(await parseError(response))
    }

    const payload = await response.json()
    optimum.value = payload.optimum
  } catch (error) {
    setError(error instanceof Error ? error.message : 'The optimum request failed.')
  } finally {
    loading.optimum = false
  }
}

async function fetchCandidates() {
  resetError()

  if (!sessionReady.value) {
    setError('Create a session before requesting top candidates.')
    return
  }

  loading.candidates = true

  try {
    const response = await fetch(`${API_PREFIX}/candidates`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        target_objective: targetObjective.value,
        top_k: topK.value,
      }),
    })

    if (!response.ok) {
      throw new Error(await parseError(response))
    }

    const payload = await response.json()
    candidates.value = payload.candidates ?? []
  } catch (error) {
    setError(error instanceof Error ? error.message : 'The candidates request failed.')
  } finally {
    loading.candidates = false
  }
}

async function runEvaluation() {
  resetError()

  if (!sessionReady.value) {
    setError('Create a session before running a manual evaluation.')
    return
  }

  loading.evaluation = true

  try {
    const response = await fetch(`${API_PREFIX}/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId.value,
        target_objective: targetObjective.value,
        parameters: { ...parameters },
      }),
    })

    if (!response.ok) {
      throw new Error(await parseError(response))
    }

    evaluation.value = await response.json()
  } catch (error) {
    setError(error instanceof Error ? error.message : 'The evaluation request failed.')
  } finally {
    loading.evaluation = false
  }
}

function applyCandidate(candidate) {
  if (!candidate?.parameters) {
    return
  }

  parameterFields.forEach((field) => {
    if (typeof candidate.parameters[field.key] === 'number') {
      parameters[field.key] = candidate.parameters[field.key]
    }
  })

  activeMode.value = 'manual'
}

function goNext() {
  if (currentStep.value === 0 && !sessionReady.value) {
    setError('Start a session before moving to the next step.')
    return
  }

  if (currentStep.value < 3) {
    stepDirection.value = 'forward'
    currentStep.value += 1
  }
}

function goBack() {
  resetError()
  if (currentStep.value > 0) {
    stepDirection.value = 'backward'
    currentStep.value -= 1
  }
}

function enterWorkspace(mode) {
  activeMode.value = mode
  stepDirection.value = 'forward'
  currentStep.value = 2
}

const transitionName = computed(() =>
  stepDirection.value === 'forward' ? 'card-slide-forward' : 'card-slide-backward',
)
</script>

<template>
  <div class="app-shell">
    <div class="background-orb background-orb-left"></div>
    <div class="background-orb background-orb-right"></div>

    <header class="brand-strip">
      <div>
        <p class="eyebrow">BioX Hackathon MVP</p>
        <h1>MediaOpt</h1>
      </div>
      <div class="brand-meta">
        <span class="meta-pill" :class="{ ready: sessionReady }">
          {{ sessionReady ? 'Session ready' : 'No active session' }}
        </span>
        <span class="meta-pill objective">{{ targetObjective }}</span>
      </div>
    </header>

    <div class="card-stack">
      <Transition :name="transitionName" mode="out-in">
        <AppCardShell
          :key="currentStep"
          :eyebrow="currentCopy.eyebrow"
          :title="currentCopy.title"
          :description="currentCopy.description"
        >
          <template #status>
            <span v-if="sessionId" class="session-pill">{{ sessionId }}</span>
          </template>

          <template #body>
            <UploadStage
              v-if="currentStep === 0"
              :upload-file-name="uploadFileName"
              :upload-loading="loading.upload"
              :target-objective="targetObjective"
              @file-change="onFileChange"
              @upload="uploadGenome"
              @update:target-objective="targetObjective = $event"
            />

            <ModeStage
              v-else-if="currentStep === 1"
              :mode="activeMode"
              :session-ready="sessionReady"
              @choose="enterWorkspace"
              @update:mode="activeMode = $event"
            />

            <WorkspaceStage
              v-else-if="currentStep === 2"
              :mode="activeMode"
              :session-ready="sessionReady"
              :target-objective="targetObjective"
              :top-k="topK"
              :best-candidate="bestAvailableCandidate"
              :candidates="candidates"
              :candidate-max-score="candidateMaxScore"
              :evaluation="evaluation"
              :diagnostics="diagnosticsEntries"
              :parameters="parameters"
              :parameter-fields="parameterFields"
              :loading-optimum="loading.optimum"
              :loading-candidates="loading.candidates"
              :loading-evaluation="loading.evaluation"
              :mode-direction="modeDirection"
              @switch-mode="activeMode = $event"
              @update:top-k="topK = $event"
              @fetch-optimum="fetchOptimum"
              @fetch-candidates="fetchCandidates"
              @apply-candidate="applyCandidate"
              @update-parameter="parameters[$event.key] = $event.value"
              @evaluate="runEvaluation"
            />

            <SummaryStage
              v-else
              :best-candidate="bestAvailableCandidate"
              :evaluation="evaluation"
              :parameter-fields="parameterFields"
              :target-objective="targetObjective"
              :summary-narrative="summaryNarrative"
            />
          </template>

          <template #footer-left>
            <button
              class="ghost-button"
              :disabled="currentStep === 0"
              @click="goBack"
            >
              Back
            </button>
          </template>

          <template #footer-center>
            <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
            <p v-else class="footnote">
              Demo input currently uses protein FASTA for the CarveMe-based workflow.
            </p>
          </template>

          <template #footer-right>
            <button
              class="primary-button"
              :disabled="currentStep === 3"
              @click="goNext"
            >
              {{ currentStep === 2 ? 'Review summary' : 'Next step' }}
            </button>
          </template>
        </AppCardShell>
      </Transition>
    </div>
  </div>
</template>
