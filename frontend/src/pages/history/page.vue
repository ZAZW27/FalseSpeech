<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { authFetch, clearToken } from '@/assets/js/api'
import { formatDateTime, formatSessionDuration, ratioToPercent } from '@/assets/js/format'
import { getVerdictMeta } from '@/assets/js/historyStats'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import Icon from '@/components/ui/icons/Icon.vue'
import HistoryTable from '@/components/history/HistoryTable.vue'
import HistoryCard from '@/components/history/HistoryCard.vue'

const PAGE_SIZE = 10
const verdictOptions = [
  { value: 'all', label: 'All' },
  { value: 'real', label: 'Real' },
  { value: 'fake', label: 'Fake' },
]

const router = useRouter()

const history = ref([])
const isLoading = ref(true)
const errorMessage = ref('')
const search = ref('')
const verdictFilter = ref('all')
const page = ref(1)

// GET /api/history -> [{ session_id, started_at, duration, fake_ratio, verdict }]
const loadHistory = async () => {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authFetch('/api/history')

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

// Raw API items -> display rows (newest first). All formatting happens here.
const rows = computed(() =>
  [...history.value]
    .sort((a, b) => new Date(b.started_at) - new Date(a.started_at))
    .map((item) => ({
      id: item.session_id,
      sessionId: `#${item.session_id}`,
      isoDate: String(item.started_at ?? ''),
      date: formatDateTime(item.started_at),
      duration: formatSessionDuration(item.duration),
      fakePercent: ratioToPercent(item.fake_ratio),
      verdict: item.verdict,
      meta: getVerdictMeta(item.verdict),
    })),
)

// Search matches the session ID or the date (formatted text or YYYY-MM-DD).
const filteredRows = computed(() => {
  const query = search.value.trim().toLowerCase().replace(/^#/, '')

  return rows.value.filter((row) => {
    const matchesVerdict = verdictFilter.value === 'all' || row.verdict === verdictFilter.value
    const matchesSearch =
      !query ||
      String(row.id).toLowerCase().includes(query) ||
      row.date.toLowerCase().includes(query) ||
      row.isoDate.slice(0, 10).includes(query)
    return matchesVerdict && matchesSearch
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / PAGE_SIZE)))
const pageRows = computed(() => filteredRows.value.slice((page.value - 1) * PAGE_SIZE, page.value * PAGE_SIZE))

const rangeLabel = computed(() => {
  const total = filteredRows.value.length
  if (!total) return 'No results'
  const from = (page.value - 1) * PAGE_SIZE + 1
  const to = Math.min(total, page.value * PAGE_SIZE)
  return `Showing ${from}-${to} of ${total} results`
})

const goPrevious = () => {
  if (page.value > 1) page.value -= 1
}
const goNext = () => {
  if (page.value < totalPages.value) page.value += 1
}

// New filter means back to the first page.
watch([search, verdictFilter], () => {
  page.value = 1
})

onMounted(loadHistory)
</script>

<template>
  <AppLayout title="Detection History" subtitle="Results of your past listening sessions.">
    <div class="flex flex-col gap-5">
      <!-- Error -->
      <div v-if="errorMessage" class="rounded-3xl border border-danger/30 bg-danger/10 p-8 text-center" role="alert">
        <p class="text-danger">{{ errorMessage }}</p>
        <BaseButton class="mt-5" @click="loadHistory">Try again</BaseButton>
      </div>

      <!-- Loading -->
      <p v-else-if="isLoading" class="py-16 text-center text-sm text-muted" role="status">Loading history...</p>

      <!-- Empty: the account has no sessions yet -->
      <div
        v-else-if="!history.length"
        class="flex flex-col items-center rounded-3xl border border-white/10 bg-white/[0.04] px-6 py-16 text-center"
      >
        <p class="max-w-[360px] text-muted">No history found. Start listening to log your first session.</p>
        <BaseButton to="/dashboard" class="mt-6">Start listening</BaseButton>
      </div>

      <template v-else>
        <!-- Filters -->
        <div class="flex flex-col gap-3 md:flex-row">
          <div class="relative flex-1">
            <label for="history-search" class="sr-only">Search by date or session ID</label>
            <span class="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted">
              <Icon name="search" :size="18" />
            </span>
            <input
              id="history-search"
              v-model="search"
              type="search"
              placeholder="Search by date or session ID"
              class="h-12 w-full rounded-xl border border-white/15 bg-white/5 pl-12 pr-4 text-sm text-white placeholder:text-muted/60 focus:border-lime-400 focus:outline-none"
            />
          </div>

          <div>
            <label for="history-verdict" class="sr-only">Filter by verdict</label>
            <select
              id="history-verdict"
              v-model="verdictFilter"
              class="h-12 w-full rounded-xl border border-white/15 bg-navy-950 px-4 text-sm text-white focus:border-lime-400 focus:outline-none md:w-[180px]"
            >
              <option v-for="option in verdictOptions" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </div>
        </div>

        <!-- No match for the current filters -->
        <p
          v-if="!filteredRows.length"
          class="rounded-3xl border border-white/10 bg-white/[0.04] px-6 py-12 text-center text-sm text-muted"
        >
          No sessions match your filters.
        </p>

        <template v-else>
          <!-- Desktop: md and up -->
          <HistoryTable class="hidden md:block" :rows="pageRows" />

          <!-- Mobile: below md -->
          <div class="flex flex-col gap-3 md:hidden">
            <HistoryCard v-for="row in pageRows" :key="row.id" :row="row" />
          </div>
        </template>

        <!-- Pagination -->
        <div class="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <p class="text-sm text-muted">{{ rangeLabel }}</p>
          <div class="flex items-center gap-3">
            <BaseButton variant="outlineLight" size="sm" :disabled="page <= 1" @click="goPrevious">Previous</BaseButton>
            <span class="text-sm text-muted">Page {{ page }} of {{ totalPages }}</span>
            <BaseButton variant="outlineLight" size="sm" :disabled="page >= totalPages" @click="goNext">Next</BaseButton>
          </div>
        </div>
      </template>
    </div>
  </AppLayout>
</template>
