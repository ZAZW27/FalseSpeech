<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { authFetch } from '@/assets/js/api'
import { summarizeHistory } from '@/assets/js/historyStats'
import { useAudioCapture } from '@/assets/js/useAudioCapture'
import PlayButton from '@/components/ui/buttons/PlayButton.vue'
import VerticalConfidence from '@/components/dashboard/VerticalConfidence.vue'
import LiveLog from '@/components/dashboard/LiveLog.vue'
import StatsRow from '@/components/dashboard/StatsRow.vue'
import ActivityChart from '@/components/dashboard/ActivityChart.vue'
import RecentDetections from '@/components/dashboard/RecentDetections.vue'

// Scenario B: paid users. user comes from AppLayout (GET /api/users/me).
const props = defineProps({
  user: { type: Object, required: true },
  updateQuota: { type: Function, required: true },
})

const { status, isListening, currentResult, liveLogs, errorMessage, start, stop } = useAudioCapture()

const history = ref([])
const historyLoading = ref(true)
const historyError = ref('')

// GET /api/history -> [{ session_id, started_at, duration, fake_ratio, verdict }]
const loadHistory = async () => {
  historyError.value = ''
  try {
    const response = await authFetch('/api/history')
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
    const data = await response.json()
    history.value = Array.isArray(data) ? data : []
  } catch {
    historyError.value = 'Could not load your history.'
  } finally {
    historyLoading.value = false
  }
}

const summary = computed(() => summarizeHistory(history.value))

const toggle = () => (isListening.value ? stop() : start({ onQuota: props.updateQuota }))

const buttonText = computed(() => {
  if (status.value === 'connecting') return 'Connecting...'
  return isListening.value ? 'Stop listening' : 'Start listening'
})

// A finished session is added to the history, so reload it when listening stops.
watch(isListening, (now, before) => {
  if (before && !now) loadHistory()
})

onMounted(loadHistory)
</script>

<template>
  <div class="flex flex-col gap-5">
    <p
      v-if="errorMessage"
      class="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <!-- Top row -->
    <div class="grid gap-5 xl:grid-cols-12">
      <section
        class="flex flex-col items-center justify-center gap-4 rounded-3xl border border-white/10 bg-gradient-to-br from-navy-800 to-[#0c5a68] p-6 xl:col-span-2"
      >
        <PlayButton size="sm" :playing="isListening" :pulse="isListening" :label="buttonText" @click="toggle" />
        <p class="text-center text-sm font-semibold">{{ buttonText }}</p>
      </section>

      <VerticalConfidence
        class="xl:col-span-4"
        :fake="currentResult ? Number(currentResult.fek_prob) : null"
        :real="currentResult ? Number(currentResult.ril_prob) : null"
      />

      <LiveLog class="xl:col-span-6" :logs="liveLogs" :listening="isListening" />
    </div>

    <!-- Middle row -->
    <StatsRow
      :used-seconds="user.quota_used"
      :limit-seconds="user.quota_limit"
      :total="summary.total"
      :ai="summary.ai"
      :human="summary.human"
    />

    <!-- Bottom row -->
    <div class="grid gap-5 xl:grid-cols-3">
      <ActivityChart class="xl:col-span-1" :history="history" />
      <RecentDetections class="xl:col-span-2" :history="history" :loading="historyLoading" :error="historyError" />
    </div>
  </div>
</template>
