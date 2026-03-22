<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import AppCardShell from './components/AppCardShell.vue'
import ModeStage from './components/ModeStage.vue'
import UploadStage from './components/UploadStage.vue'
import WorkspaceStage from './components/WorkspaceStage.vue'

const API_PREFIX = '/api'
const ALLOWED_UPLOAD_SUFFIXES = ['.faa', '.fa', '.fasta']
const DEFAULT_MOCK_PATH = '/mock/biox_tuning_results.json'

const parameterFields = [
  {
    key: 'EX_cellb_e',
    label: 'Cellobiose',
    hint: 'Complex carbon source',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_glc__D_e',
    label: 'Glucose',
    hint: 'Primary carbon source',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_glyc_e',
    label: 'Glycerol',
    hint: 'Alternative carbon source',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_nh4_e',
    label: 'Ammonium',
    hint: 'Nitrogen supply',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_o2_e',
    label: 'Oxygen',
    hint: 'Aeration window',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_pi_e',
    label: 'Phosphate',
    hint: 'Phosphorus balance',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_so4_e',
    label: 'Sulfate',
    hint: 'Sulfur source',
    min: -15,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_xyl__D_e',
    label: 'Xylose',
    hint: 'Alternative sugar source',
    min: -15,
    max: 15,
    step: 0.1,
  },
]

const stepTitles = [
  {
    title: 'Create a model session',
    description: '',
  },
  {
    title: 'Choose an exploration path',
    description: 'Pick the workflow you want to enter first. You can still switch inside the workspace.',
  },
  {
    title: 'Explore candidate conditions',
    description: 'Move between recommended and manual exploration without leaving the same workspace.',
  },
]

const currentStep = ref(0)
const stepDirection = ref('forward')
const activeMode = ref('recommended')
const uploadFile = ref(null)
const uploadFileName = ref('')
const sessionId = ref('')
const modelPath = ref('')
const errorMessage = ref('')
const infoMessage = ref('')
const mockResults = ref({})
const selectedMockAccession = ref('')

const loading = reactive({
  upload: false,
  evaluation: false,
})

const parameters = reactive({
  EX_cellb_e: -0.1,
  EX_glc__D_e: -0.1,
  EX_glyc_e: -0.1,
  EX_nh4_e: -0.1,
  EX_o2_e: -2,
  EX_pi_e: -0.1,
  EX_so4_e: -2,
  EX_xyl__D_e: -0.1,
})

const TOP_K = 10
const selectedCandidateIndex = ref(0)
const evaluation = ref(null)

const sessionReady = computed(() => Boolean(sessionId.value))
const currentCopy = computed(() => {
  if (currentStep.value !== 2) {
    return stepTitles[currentStep.value]
  }

  if (activeMode.value === 'recommended') {
    return {
      title: 'Review optimization suggestions',
      description: 'Inspect the precomputed best condition and compare the strongest suggested media settings for the selected demo profile.',
    }
  }

  return {
    title: 'Simulate a parameter set',
    description: '',
  }
})
const profileOptions = computed(() => Object.keys(mockResults.value).sort())
const mockRecordsForSelection = computed(() =>
  selectedMockAccession.value ? mockResults.value[selectedMockAccession.value] ?? [] : [],
)

const bestAvailableCandidate = computed(() => {
  if (!mockRecordsForSelection.value.length) {
    return null
  }

  const best = [...mockRecordsForSelection.value].sort((left, right) => left.cost - right.cost)[0]
  return normalizeMockCandidate(best)
})

const displayCandidates = computed(() => {
  if (!mockRecordsForSelection.value.length) {
    return []
  }

  const candidateList = [...mockRecordsForSelection.value]
    .sort((left, right) => left.cost - right.cost)
    .slice(0, TOP_K)
    .map(normalizeMockCandidate)

  const costs = candidateList
    .map((candidate) => Number(candidate.cost ?? 0))
    .filter((value) => Number.isFinite(value))

  const minCost = Math.min(...costs)
  const maxCost = Math.max(...costs)

  return candidateList.map((candidate) => {
    const cost = Number(candidate.cost ?? 0)
    const ratio = maxCost === minCost ? 1 : (maxCost - cost) / (maxCost - minCost)
    return {
      ...candidate,
      barWidth: `${35 + ratio * 65}%`,
    }
  })
})

const selectedDisplayCandidate = computed(() => {
  if (!displayCandidates.value.length) {
    return bestAvailableCandidate.value
  }

  const safeIndex = Math.min(selectedCandidateIndex.value, displayCandidates.value.length - 1)
  return displayCandidates.value[safeIndex]
})

const diagnosticsEntries = computed(() => {
  if (!evaluation.value?.diagnostics) {
    return []
  }

  return Object.entries(evaluation.value.diagnostics)
})

function resetError() {
  errorMessage.value = ''
}

function setError(message) {
  errorMessage.value = message || 'The request failed.'
}

function setInfo(message) {
  infoMessage.value = message || ''
}

function isAllowedFile(fileName) {
  const lowerName = fileName.toLowerCase()
  return ALLOWED_UPLOAD_SUFFIXES.some((suffix) => lowerName.endsWith(suffix))
}

function onFileChange(event) {
  resetError()
  setInfo('')
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

function formatDecimal(value) {
  const numericValue = Number(value)
  return Number.isFinite(numericValue) ? numericValue.toFixed(3) : 'N/A'
}

function normalizeMockCandidate(record) {
  return {
    id: record.config_id,
    cost: Number(record.cost),
    status: record.status,
    time: record.time,
    parameters: { ...record.config },
    rawParameters: record.config,
    metadata: {
      config_id: record.config_id,
      status: record.status,
      time: record.time,
      cpu_time: record.cpu_time,
    },
  }
}

function syncParametersFromCandidate(candidate) {
  if (!candidate?.parameters) {
    return
  }

  evaluation.value = null

  parameterFields.forEach((field) => {
    if (typeof candidate.parameters[field.key] === 'number') {
      parameters[field.key] = candidate.parameters[field.key]
    }
  })
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
  setInfo('')

  if (!selectedMockAccession.value) {
    setError('Select a demo profile before uploading your FASTA file.')
    return
  }

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
    evaluation.value = null
    if (selectedMockAccession.value) {
      const firstMockCandidate = normalizeMockCandidate(mockResults.value[selectedMockAccession.value][0])
      syncParametersFromCandidate(firstMockCandidate)
      selectedCandidateIndex.value = 0
      setInfo(`Using demo profile ${selectedMockAccession.value}.`)
    }

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
    setError('Create a session before reviewing optimization suggestions.')
  }
}

async function fetchCandidates() {
  resetError()

  if (!sessionReady.value) {
    setError('Create a session before reviewing optimization suggestions.')
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
  syncParametersFromCandidate(candidate)
  activeMode.value = 'manual'
}

function goNext() {
  if (currentStep.value === 0 && !sessionReady.value) {
    setError('Start a session before moving to the next step.')
    return
  }

  if (currentStep.value === 1) {
    enterWorkspace(activeMode.value)
    return
  }

  if (currentStep.value < 2) {
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

function switchWorkspaceMode(mode) {
  activeMode.value = mode
}

function selectCandidate(index) {
  if (!displayCandidates.value.length) {
    selectedCandidateIndex.value = 0
    return
  }

  const maxIndex = displayCandidates.value.length - 1
  selectedCandidateIndex.value = Math.max(0, Math.min(index, maxIndex))
}

function updateParameter({ key, value }) {
  parameters[key] = value
  evaluation.value = null
}

const transitionName = computed(() =>
  stepDirection.value === 'forward' ? 'card-slide-forward' : 'card-slide-backward',
)

async function loadMockResults() {
  try {
    const response = await fetch(DEFAULT_MOCK_PATH)
    if (!response.ok) {
      throw new Error(`Mock data request failed with status ${response.status}.`)
    }

    mockResults.value = await response.json()
    if (!selectedMockAccession.value) {
      selectedMockAccession.value = Object.keys(mockResults.value)[0] ?? ''
    }
  } catch (error) {
    setError(error instanceof Error ? error.message : 'The mock data request failed.')
  }
}

onMounted(() => {
  loadMockResults()
})
</script>

<template>
  <div class="app-shell">
    <div class="background-orb background-orb-left"></div>
    <div class="background-orb background-orb-right"></div>

    <header class="brand-strip">
      <div>
        <p class="eyebrow">BioX - BioHackathon Edinburgh 2026</p>
        <h1>MediaOpt</h1>
      </div>
    </header>

    <div class="card-stack">
      <Transition :name="transitionName" mode="out-in">
        <AppCardShell
          :key="currentStep"
          :title="currentCopy.title"
          :description="currentCopy.description"
        >
          <template #body>
            <UploadStage
              v-if="currentStep === 0"
              :upload-file-name="uploadFileName"
              :upload-loading="loading.upload"
              :profile-options="profileOptions"
              :selected-profile="selectedMockAccession"
              @file-change="onFileChange"
              @update:selected-profile="selectedMockAccession = $event"
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
              :mock-accession="selectedMockAccession"
              :top-k="TOP_K"
              :best-candidate="bestAvailableCandidate"
              :candidates="displayCandidates"
              :selected-candidate="selectedDisplayCandidate"
              :selected-candidate-index="selectedCandidateIndex"
              :evaluation="evaluation"
              :diagnostics="diagnosticsEntries"
              :parameters="parameters"
            :parameter-fields="parameterFields"
            :format-decimal="formatDecimal"
            :loading-evaluation="loading.evaluation"
            @switch-mode="switchWorkspaceMode"
            @select-candidate="selectCandidate"
            @apply-candidate="applyCandidate"
            @update-parameter="updateParameter"
            @evaluate="runEvaluation"
          />

          </template>

          <template #footer-left>
            <button
              v-if="currentStep > 0"
              class="ghost-button"
              @click="goBack"
            >
              Back
            </button>
          </template>

          <template #footer-center>
            <p v-if="errorMessage" class="inline-error">{{ errorMessage }}</p>
            <p v-else-if="infoMessage" class="footnote">{{ infoMessage }}</p>
            <p v-else class="footnote">
              
            </p>
          </template>

          <template #footer-right>
            <button
              v-if="currentStep < 2"
              class="primary-button"
              :disabled="currentStep === 0 && (loading.upload || !selectedMockAccession)"
              @click="currentStep === 0 ? uploadGenome() : goNext()"
            >
              {{
                currentStep === 0
                  ? (loading.upload ? 'Preparing workspace...' : 'Upload and continue')
                  : (
                      activeMode === 'recommended'
                        ? 'Open optimization suggestions'
                        : 'Open parameter simulation'
                    )
              }}
            </button>
          </template>
        </AppCardShell>
      </Transition>
    </div>
  </div>
</template>
