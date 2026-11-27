<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { authFetch, clearToken } from '@/assets/js/api'
import { formatDateTime } from '@/assets/js/format'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import PageSkeleton from '@/components/ui/skeletons/PageSkeleton.vue'
import Icon from '@/components/ui/icons/Icon.vue'
import HistorySessionItem from '@/components/history/HistorySessionItem.vue'
import ExportPreviewModal from '@/components/history/ExportPreviewModal.vue'

const PAGE_SIZE = 10

const verdictOptions = [
  { value: 'all', label: 'All Verdicts' },
  { value: 'real', label: 'Human Only (Real)' },
  { value: 'fake', label: 'AI Voice (Fake)' },
  { value: 'mixed', label: 'Mixed Risk' },
  { value: 'has_fake', label: 'Any AI Flagged' },
]

const sourceOptions = [
  { value: 'all', label: 'All Sources' },
  { value: 'web', label: 'Web Live' },
  { value: 'upload', label: 'Recorded Upload' },
  { value: 'android', label: 'Android App' },
]

const sortOptions = [
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
  { value: 'highest_risk', label: 'Highest AI Risk' },
  { value: 'most_chunks', label: 'Most Chunks' },
]

const router = useRouter()

const history = ref([])
const isLoading = ref(true)
const errorMessage = ref('')
const toastMessage = ref('')

// Filters
const search = ref('')
const verdictFilter = ref('all')
const sourceFilter = ref('all')
const sortBy = ref('newest')
const startDate = ref('')
const endDate = ref('')
const activePreset = ref('all')
const page = ref(1)

// Expanded sessions & cached chunks per session_id
const expandedIds = reactive(new Set())
const segmentsBySession = reactive({})
const loadingSegmentsBySession = reactive({})

// Google Docs-style Export Preview Modal state
const exportModalOpen = ref(false)
const exportSessionId = ref(null)
const exportSessionTitle = ref('')

const showToast = (msg) => {
  toastMessage.value = msg
  setTimeout(() => {
    if (toastMessage.value === msg) toastMessage.value = ''
  }, 3000)
}

const openExportModal = ({ sessionId = null, title = '' } = {}) => {
  exportSessionId.value = sessionId
  exportSessionTitle.value = title
  exportModalOpen.value = true
}

const activeExportFilters = computed(() => ({
  verdict: verdictFilter.value,
  source: sourceFilter.value,
  search: search.value.trim(),
  startDate: startDate.value,
  endDate: endDate.value,
}))

const loadHistory = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authFetch('/api/history?limit=300')

    if (response.status === 401) {
      clearToken()
      router.replace('/login')
      return
    }
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)

    const data = await response.json()
    history.value = Array.isArray(data) ? data : []
  } catch {
    errorMessage.value = 'Could not load your history. Please try again.'
  } finally {
    isLoading.value = false
  }
}

const loadSessionSegments = async (sessionId) => {
  if (segmentsBySession[sessionId] || loadingSegmentsBySession[sessionId]) return
  loadingSegmentsBySession[sessionId] = true
  try {
    const res = await authFetch(`/api/history/${encodeURIComponent(sessionId)}`)
    if (res.status === 401) {
      clearToken()
      router.replace('/login')
      return
    }
    if (!res.ok) throw new Error('Failed to load session chunks')
    const detail = await res.json()
    segmentsBySession[sessionId] = Array.isArray(detail.segments) ? detail.segments : []
  } catch {
    segmentsBySession[sessionId] = []
  } finally {
    loadingSegmentsBySession[sessionId] = false
  }
}

const toggleSession = (sessionId) => {
  if (expandedIds.has(sessionId)) {
    expandedIds.delete(sessionId)
  } else {
    expandedIds.add(sessionId)
    loadSessionSegments(sessionId)
  }
}

const toLocalDatetimeInput = (date) => {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

const applyDatePreset = (preset) => {
  activePreset.value = preset
  if (preset === 'all') {
    startDate.value = ''
    endDate.value = ''
    return
  }
  const now = new Date()
  const from = new Date(now)
  if (preset === 'today') {
    from.setHours(0, 0, 0, 0)
  } else if (preset === '7d') {
    from.setDate(now.getDate() - 7)
  } else if (preset === '30d') {
    from.setDate(now.getDate() - 30)
  }
  startDate.value = toLocalDatetimeInput(from)
  endDate.value = toLocalDatetimeInput(now)
}

const clearFilters = () => {
  search.value = ''
  verdictFilter.value = 'all'
  sourceFilter.value = 'all'
  sortBy.value = 'newest'
  startDate.value = ''
  endDate.value = ''
  activePreset.value = 'all'
}

const hasActiveFilters = computed(
  () =>
    Boolean(search.value.trim()) ||
    verdictFilter.value !== 'all' ||
    sourceFilter.value !== 'all' ||
    Boolean(startDate.value) ||
    Boolean(endDate.value),
)

const filteredSessions = computed(() => {
  const query = search.value.trim().toLowerCase().replace(/^#/, '')
  const fromMs = startDate.value ? new Date(startDate.value).getTime() : null
  const toMs = endDate.value ? new Date(endDate.value).getTime() : null

  const filtered = history.value.filter((item) => {
    if (verdictFilter.value === 'has_fake') {
      if ((item.fake_count || 0) <= 0 && item.verdict !== 'fake' && item.verdict !== 'mixed') return false
    } else if (verdictFilter.value !== 'all' && item.verdict !== verdictFilter.value) {
      return false
    }

    const src = String(item.source || 'web').toLowerCase()
    if (sourceFilter.value !== 'all' && src !== sourceFilter.value) return false

    const itemMs = new Date(item.started_at).getTime()
    if (fromMs !== null && !Number.isNaN(fromMs) && itemMs < fromMs) return false
    if (toMs !== null && !Number.isNaN(toMs) && itemMs > toMs) return false

    if (query) {
      const formattedDate = formatDateTime(item.started_at).toLowerCase()
      const haystack = [
        item.session_id,
        item.title || '',
        item.notes || '',
        item.verdict || '',
        src,
        String(item.started_at || ''),
        formattedDate,
      ]
        .join(' ')
        .toLowerCase()
      if (!haystack.includes(query)) return false
    }

    return true
  })

  return filtered.sort((a, b) => {
    if (sortBy.value === 'oldest') return new Date(a.started_at) - new Date(b.started_at)
    if (sortBy.value === 'highest_risk') return (b.fake_ratio || 0) - (a.fake_ratio || 0)
    if (sortBy.value === 'most_chunks') return (b.total_chunks || 0) - (a.total_chunks || 0)
    return new Date(b.started_at) - new Date(a.started_at)
  })
})

const kpiSummary = computed(() => {
  const list = filteredSessions.value
  const totalSessions = list.length
  const totalChunks = list.reduce((acc, s) => acc + (Number(s.total_chunks) || 0), 0)
  const fakeChunks = list.reduce((acc, s) => acc + (Number(s.fake_count) || 0), 0)
  const aiSessions = list.filter((s) => (s.fake_count || 0) > 0 || s.verdict === 'fake' || s.verdict === 'mixed').length
  const humanSessions = totalSessions - aiSessions
  const avgRisk = totalSessions
    ? Math.round((list.reduce((acc, s) => acc + (Number(s.fake_ratio) || 0), 0) / totalSessions) * 100)
    : 0
  return { totalSessions, totalChunks, fakeChunks, aiSessions, humanSessions, avgRisk }
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredSessions.value.length / PAGE_SIZE)))
const pageSessions = computed(() =>
  filteredSessions.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE),
)

const allPageExpanded = computed(
  () => pageSessions.value.length > 0 && pageSessions.value.every((s) => expandedIds.has(s.session_id)),
)

const toggleExpandAllOnPage = () => {
  if (allPageExpanded.value) {
    pageSessions.value.forEach((s) => expandedIds.delete(s.session_id))
  } else {
    pageSessions.value.forEach((s) => {
      expandedIds.add(s.session_id)
      loadSessionSegments(s.session_id)
    })
  }
}

const rangeLabel = computed(() => {
  const total = filteredSessions.value.length
  if (!total) return 'No sessions'
  const from = (page.value - 1) * PAGE_SIZE + 1
  const to = Math.min(total, page.value * PAGE_SIZE)
  return `Showing ${from}-${to} of ${total} session${total === 1 ? '' : 's'}`
})

const goPrevious = () => {
  if (page.value > 1) page.value -= 1
}
const goNext = () => {
  if (page.value < totalPages.value) page.value += 1
}

const handleSaveMeta = async ({ sessionId, title, notes }) => {
  try {
    const res = await authFetch(`/api/history/${encodeURIComponent(sessionId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, notes }),
    })
    if (!res.ok) throw new Error('Update failed')
    const updated = await res.json()
    const idx = history.value.findIndex((s) => s.session_id === sessionId)
    if (idx !== -1) history.value[idx] = { ...history.value[idx], ...updated }
    showToast('Session label & HR notes saved.')
  } catch {
    showToast('Could not save session notes. Please try again.')
  }
}

const handleDeleteSession = async (sessionId) => {
  try {
    const res = await authFetch(`/api/history/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
    if (!res.ok && res.status !== 204) throw new Error('Delete failed')
    history.value = history.value.filter((s) => s.session_id !== sessionId)
    expandedIds.delete(sessionId)
    delete segmentsBySession[sessionId]
    showToast(`Session #${sessionId} deleted.`)
  } catch {
    showToast('Could not delete session.')
  }
}

watch([search, verdictFilter, sourceFilter, startDate, endDate, sortBy], () => {
  page.value = 1
})

onMounted(loadHistory)
</script>

<template>
  <AppLayout
    title="Detection History"
    subtitle="Review grouped listening sessions, inspect per-chunk detections, annotate candidate notes, and export HR reports."
  >
    <div class="flex flex-col gap-5">
      <!-- Toast feedback -->
      <div
        v-if="toastMessage"
        class="rounded-xl border border-white/15 bg-white/10 px-4 py-2.5 text-xs font-semibold text-white"
        role="status"
      >
        {{ toastMessage }}
      </div>

      <!-- Error -->
      <div v-if="errorMessage" class="rounded-3xl border-2 border-red-400/30 bg-red-400/10 p-8 text-center" role="alert">
        <p class="text-red-400">{{ errorMessage }}</p>
        <BaseButton class="mt-5" @click="loadHistory">Try again</BaseButton>
      </div>

      <!-- Loading -->
      <PageSkeleton v-else-if="isLoading" variant="history" :show-header="false" />

      <!-- Empty: no sessions yet -->
      <div
        v-else-if="!history.length"
        class="flex flex-col items-center rounded-3xl border-2 border-back-secondary bg-back-secondary/40 px-6 py-16 text-center"
      >
        <p class="max-w-[360px] text-slate-300">No history found. Start listening to log your first session.</p>
        <BaseButton to="/dashboard" class="mt-6">Start listening</BaseButton>
      </div>

      <template v-else>
        <!-- HR KPI Overview Strip (Soft off-white numbers + neutral slate labels) -->
        <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <div class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 px-5 py-4">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Sessions Shown</p>
            <p class="mt-1.5 text-2xl font-extrabold tabular-nums text-slate-100">{{ kpiSummary.totalSessions }}</p>
            <p class="mt-0.5 text-xs text-slate-400">{{ kpiSummary.totalChunks }} analyzed chunks</p>
          </div>

          <div class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 px-5 py-4">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">AI Flagged Sessions</p>
            <p class="mt-1.5 text-2xl font-extrabold tabular-nums text-slate-100">{{ kpiSummary.aiSessions }}</p>
            <p class="mt-0.5 text-xs text-slate-400">{{ kpiSummary.fakeChunks }} suspicious chunk(s)</p>
          </div>

          <div class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 px-5 py-4">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Human Verified</p>
            <p class="mt-1.5 text-2xl font-extrabold tabular-nums text-slate-100">{{ kpiSummary.humanSessions }}</p>
            <p class="mt-0.5 text-xs text-slate-400">Clean sessions with no AI flags</p>
          </div>

          <div class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 px-5 py-4">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Average AI Risk</p>
            <p class="mt-1.5 text-2xl font-extrabold tabular-nums text-slate-100">{{ kpiSummary.avgRisk }}%</p>
            <p class="mt-0.5 text-xs text-slate-400">Across current filtered view</p>
          </div>
        </div>

        <!-- HR Search, Time-Range Filters & Single Export Modal Trigger -->
        <section class="flex flex-col gap-4 rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-5">
          <!-- Row 1: Search + Verdict + Source + Sort -->
          <div class="grid gap-3 md:grid-cols-12">
            <div class="relative md:col-span-5">
              <label for="history-search" class="sr-only">Search sessions</label>
              <span class="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400">
                <Icon name="search" :size="17" />
              </span>
              <input
                id="history-search"
                v-model="search"
                type="search"
                placeholder="Search candidate, HR notes, #ID, or date..."
                class="h-11 w-full rounded-xl border border-white/15 bg-white/5 pl-10 pr-4 text-sm text-white placeholder:text-slate-400 focus:border-white/40 focus:outline-none"
              />
            </div>

            <div class="md:col-span-3">
              <label for="history-verdict" class="sr-only">Filter by verdict</label>
              <select
                id="history-verdict"
                v-model="verdictFilter"
                class="h-11 w-full rounded-xl border border-white/15 bg-back-prime px-3.5 text-sm text-white focus:border-white/40 focus:outline-none"
              >
                <option v-for="option in verdictOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="md:col-span-2">
              <label for="history-source" class="sr-only">Filter by source</label>
              <select
                id="history-source"
                v-model="sourceFilter"
                class="h-11 w-full rounded-xl border border-white/15 bg-back-prime px-3.5 text-sm text-white focus:border-white/40 focus:outline-none"
              >
                <option v-for="option in sourceOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div class="md:col-span-2">
              <label for="history-sort" class="sr-only">Sort sessions</label>
              <select
                id="history-sort"
                v-model="sortBy"
                class="h-11 w-full rounded-xl border border-white/15 bg-back-prime px-3.5 text-sm text-white focus:border-white/40 focus:outline-none"
              >
                <option v-for="option in sortOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>

          <!-- Row 2: Between Times (From / To) + Quick Presets + Clean Export Button -->
          <div class="flex flex-col gap-3 border-t border-white/10 pt-3.5 lg:flex-row lg:items-end lg:justify-between">
            <div class="flex flex-wrap items-end gap-3">
              <div>
                <label for="history-start" class="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  From Date &amp; Time
                </label>
                <input
                  id="history-start"
                  v-model="startDate"
                  type="datetime-local"
                  class="mt-1 h-10 rounded-xl border border-white/15 bg-back-prime px-3 text-xs text-white focus:border-white/40 focus:outline-none"
                  @input="activePreset = 'custom'"
                />
              </div>

              <div>
                <label for="history-end" class="block text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  To Date &amp; Time
                </label>
                <input
                  id="history-end"
                  v-model="endDate"
                  type="datetime-local"
                  class="mt-1 h-10 rounded-xl border border-white/15 bg-back-prime px-3 text-xs text-white focus:border-white/40 focus:outline-none"
                  @input="activePreset = 'custom'"
                />
              </div>

              <div class="flex flex-wrap items-center gap-1.5">
                <button
                  v-for="preset in [
                    { id: 'all', label: 'All Time' },
                    { id: 'today', label: 'Today' },
                    { id: '7d', label: 'Last 7d' },
                    { id: '30d', label: 'Last 30d' },
                  ]"
                  :key="preset.id"
                  type="button"
                  :class="[
                    'h-10 rounded-xl border px-3 text-xs font-semibold transition',
                    activePreset === preset.id
                      ? 'border-white bg-white text-back-prime'
                      : 'border-white/15 bg-white/5 text-slate-300 hover:border-white/30 hover:text-white',
                  ]"
                  @click="applyDatePreset(preset.id)"
                >
                  {{ preset.label }}
                </button>

                <button
                  v-if="hasActiveFilters"
                  type="button"
                  class="h-10 rounded-xl border border-white/15 bg-white/5 px-3 text-xs font-semibold text-slate-300 transition hover:bg-white/15 hover:text-white"
                  @click="clearFilters"
                >
                  Reset
                </button>
              </div>
            </div>

            <!-- Single clean Export button (green with crisp white text -> opens preview modal) -->
            <div class="flex items-center">
              <button
                type="button"
                :disabled="!filteredSessions.length"
                class="h-10 rounded-xl border border-brand-green/40 bg-[#2f6b5e] px-5 text-xs font-bold text-slate-100 shadow-sm transition hover:bg-[#387c6d] disabled:opacity-40"
                @click="openExportModal()"
              >
                Export Report
              </button>
            </div>
          </div>
        </section>

        <!-- List Header + Expand/Collapse All -->
        <div v-if="filteredSessions.length" class="flex items-center justify-between px-1">
          <p class="text-xs text-slate-400">
            Click any session row to inspect its audio chunks, edit candidate notes, or export an individual report.
          </p>
          <button
            type="button"
            class="shrink-0 rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-white/15"
            @click="toggleExpandAllOnPage"
          >
            {{ allPageExpanded ? 'Collapse All' : 'Expand All' }}
          </button>
        </div>

        <!-- No match for filters -->
        <p
          v-if="!filteredSessions.length"
          class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 px-6 py-12 text-center text-sm text-slate-400"
        >
          No sessions match your current filters.
        </p>

        <!-- Session Dropdown List -->
        <div v-else class="flex flex-col gap-3">
          <HistorySessionItem
            v-for="session in pageSessions"
            :key="session.session_id"
            :session="session"
            :expanded="expandedIds.has(session.session_id)"
            :segments="segmentsBySession[session.session_id] ?? null"
            :loading-segments="Boolean(loadingSegmentsBySession[session.session_id])"
            @toggle="toggleSession"
            @save-meta="handleSaveMeta"
            @delete="handleDeleteSession"
            @open-export="openExportModal"
          />
        </div>

        <!-- Pagination -->
        <div class="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p class="text-sm text-slate-400">{{ rangeLabel }}</p>
          <div class="flex items-center gap-3">
            <BaseButton variant="outlineLight" size="sm" :disabled="page <= 1" @click="goPrevious">Previous</BaseButton>
            <span class="text-sm text-slate-400">Page {{ page }} of {{ totalPages }}</span>
            <BaseButton variant="outlineLight" size="sm" :disabled="page >= totalPages" @click="goNext">Next</BaseButton>
          </div>
        </div>
      </template>
    </div>

    <!-- Google Docs-style Floating Export & Live Preview Modal -->
    <ExportPreviewModal
      v-model="exportModalOpen"
      :session-id="exportSessionId"
      :session-title="exportSessionTitle"
      :filters="activeExportFilters"
      @downloaded="(file) => showToast(`Downloaded ${file}`)"
    />
  </AppLayout>
</template>
