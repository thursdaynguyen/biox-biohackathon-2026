<script setup>
import { computed, onMounted, reactive, ref } from 'vue'

import AppCardShell from './components/AppCardShell.vue'
import ModeStage from './components/ModeStage.vue'
import SummaryStage from './components/SummaryStage.vue'
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
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_glc__D_e',
    label: 'Glucose',
    hint: 'Primary carbon source',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_glyc_e',
    label: 'Glycerol',
    hint: 'Alternative carbon source',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_nh4_e',
    label: 'Ammonium',
    hint: 'Nitrogen supply',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_o2_e',
    label: 'Oxygen',
    hint: 'Aeration window',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_pi_e',
    label: 'Phosphate',
    hint: 'Phosphorus balance',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_so4_e',
    label: 'Sulfate',
    hint: 'Sulfur source',
    min: 0,
    max: 15,
    step: 0.1,
  },
  {
    key: 'EX_xyl__D_e',
    label: 'Xylose',
    hint: 'Alternative sugar source',
    min: 0,
    max: 15,
    step: 0.1,
  },
]

const stepTitles = [
  {
    eyebrow: 'Step 1 of 4',
    title: 'Create a model session',
    description: 'Start the demo with a protein FASTA file and attach it to the closest precomputed optimization profile.',
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
  optimum: false,
  candidates: false,
  evaluation: false,
})

const parameters = reactive({
  EX_cellb_e: 0.1,
  EX_glc__D_e: 0.1,
  EX_glyc_e: 0.1,
  EX_nh4_e: 0.1,
  EX_o2_e: 2,
  EX_pi_e: 0.1,
  EX_so4_e: 2,
  EX_xyl__D_e: 0.1,
})

const topK = ref(5)
const optimum = ref(null)
const candidates = ref([])
const evaluation = ref(null)

const sessionReady = computed(() => Boolean(sessionId.value))
const currentCopy = computed(() => stepTitles[currentStep.value])
const modeDirection = computed(() => (activeMode.value === 'recommended' ? 'recommended' : 'manual'))
const mockRecordsForSelection = computed(() =>
  selectedMockAccession.value ? mockResults.value[selectedMockAccession.value] ?? [] : [],
)

const bestAvailableCandidate = computed(() => {
  if (optimum.value?.parameters) {
    return optimum.value
  }

  if (candidates.value.length > 0) {
    return candidates.value[0]
  }

  return null
})

const displayCandidates = computed(() => {
  if (!candidates.value.length) {
    return []
  }

  const costs = candidates.value
    .map((candidate) => Number(candidate.cost ?? 0))
    .filter((value) => Number.isFinite(value))

  const minCost = Math.min(...costs)
  const maxCost = Math.max(...costs)

  return candidates.value.map((candidate) => {
    const cost = Number(candidate.cost ?? 0)
    const ratio = maxCost === minCost ? 1 : (maxCost - cost) / (maxCost - minCost)
    return {
      ...candidate,
      barWidth: `${35 + ratio * 65}%`,
    }
  })
})

const diagnosticsEntries = computed(() => {
  if (!evaluation.value?.diagnostics) {
    return []
  }

  return Object.entries(evaluation.value.diagnostics)
})

const summaryNarrative = computed(() => {
  if (evaluation.value && bestAvailableCandidate.value) {
    return 'The mock optimization profile gives you the lowest-cost candidate, while the manual run shows how your custom condition behaves in the live model.'
  }

  if (bestAvailableCandidate.value) {
    return 'The strongest available recommendation currently comes from the precomputed optimization profile.'
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

function accessionFromFileName(fileName) {
  const match = fileName.match(/GCA_\d+\.\d+/i)
  return match ? match[0].toUpperCase() : ''
}

function profileIdFromModelPath(pathValue) {
  if (!pathValue) {
    return ''
  }

  const normalizedSegments = String(pathValue)
    .split(/[\\/]/)
    .filter(Boolean)

  if (!normalizedSegments.length) {
    return ''
  }

  const fileName = normalizedSegments.at(-1) ?? ''
  const parentName = normalizedSegments.length > 1 ? normalizedSegments.at(-2) ?? '' : ''
  const baseName = fileName.replace(/\.xml$/i, '')

  const candidates = [baseName, parentName]

  for (const candidate of candidates) {
    if (candidate && mockResults.value[candidate]) {
      return candidate
    }
  }

  for (const candidate of candidates) {
    const accession = accessionFromFileName(candidate)
    if (accession && mockResults.value[accession]) {
      return accession
    }
  }

  return ''
}

function toUiMagnitude(value) {
  return Number(Math.abs(Number(value ?? 0)).toFixed(3))
}

function toModelBound(value) {
  return -Math.abs(Number(value ?? 0))
}

function normalizeMockCandidate(record) {
  return {
    id: record.config_id,
    cost: Number(record.cost),
    status: record.status,
    time: record.time,
    parameters: Object.fromEntries(
      Object.entries(record.config).map(([key, value]) => [key, toUiMagnitude(value)]),
    ),
    rawParameters: record.config,
    metadata: {
      config_id: record.config_id,
      status: record.status,
      time: record.time,
      cpu_time: record.cpu_time,
    },
  }
}

function resolveMockAccession(pathValue, fileName) {
  const keys = Object.keys(mockResults.value)

  if (!keys.length) {
    return ''
  }

  const modelProfile = profileIdFromModelPath(pathValue)
  if (modelProfile) {
    return modelProfile
  }

  const accession = accessionFromFileName(fileName)
  if (accession && mockResults.value[accession]) {
    return accession
  }

  return keys[0]
}

function syncParametersFromCandidate(candidate) {
  if (!candidate?.parameters) {
    return
  }

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
    selectedMockAccession.value = resolveMockAccession(payload.model_path, uploadFileName.value)

    if (selectedMockAccession.value) {
      const firstMockCandidate = normalizeMockCandidate(mockResults.value[selectedMockAccession.value][0])
      syncParametersFromCandidate(firstMockCandidate)

      const matchedModelProfile = profileIdFromModelPath(payload.model_path)
      const matchedAccession = accessionFromFileName(uploadFileName.value)

      if (matchedModelProfile && matchedModelProfile === selectedMockAccession.value) {
        setInfo(`Mock optimization profile matched from the generated GEM profile: ${selectedMockAccession.value}.`)
      } else if (matchedAccession && matchedAccession === selectedMockAccession.value) {
        setInfo(`Mock optimization profile matched from the uploaded filename: ${selectedMockAccession.value}.`)
      } else {
        setInfo(`No exact GEM profile match was found. Using demo profile ${selectedMockAccession.value}.`)
      }
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
    setError('Create a session before requesting the recommended setup.')
    return
  }

  loading.optimum = true

  try {
    if (!mockRecordsForSelection.value.length) {
      throw new Error('No mock optimization profile is available for this session.')
    }

    const best = [...mockRecordsForSelection.value].sort((left, right) => left.cost - right.cost)[0]
    optimum.value = normalizeMockCandidate(best)
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
    if (!mockRecordsForSelection.value.length) {
      throw new Error('No mock optimization profile is available for this session.')
    }

    candidates.value = [...mockRecordsForSelection.value]
      .sort((left, right) => left.cost - right.cost)
      .slice(0, topK.value)
      .map(normalizeMockCandidate)
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
        parameters: Object.fromEntries(
          Object.entries(parameters).map(([key, value]) => [key, toModelBound(value)]),
        ),
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

async function loadMockResults() {
  try {
    const response = await fetch(DEFAULT_MOCK_PATH)
    if (!response.ok) {
      throw new Error(`Mock data request failed with status ${response.status}.`)
    }

    mockResults.value = await response.json()
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
        <p class="eyebrow">BioX Hackathon MVP</p>
        <h1>MediaOpt</h1>
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
          <template #body>
            <UploadStage
              v-if="currentStep === 0"
              :upload-file-name="uploadFileName"
              :upload-loading="loading.upload"
              @file-change="onFileChange"
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
              :top-k="topK"
              :best-candidate="bestAvailableCandidate"
              :candidates="displayCandidates"
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
              :mock-accession="selectedMockAccession"
              :summary-narrative="summaryNarrative"
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
              Demo input currently uses protein FASTA for the CarveMe-based workflow.
            </p>
          </template>

          <template #footer-right>
            <button
              class="primary-button"
              :disabled="currentStep === 3 || (currentStep === 0 && loading.upload)"
              @click="currentStep === 0 ? uploadGenome() : goNext()"
            >
              {{
                currentStep === 0
                  ? (loading.upload ? 'Preparing workspace...' : 'Upload and continue')
                  : currentStep === 2
                    ? 'Review summary'
                    : 'Next step'
              }}
            </button>
          </template>
        </AppCardShell>
      </Transition>
    </div>
  </div>
</template>
