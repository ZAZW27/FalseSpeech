<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { authFetch } from '@/assets/js/api'
import { summarizeHistory } from '@/assets/js/historyStats'
import { useAudioCapture } from '@/assets/js/useAudioCapture'
import PlayButton from '@/components/ui/buttons/PlayButton.vue'
import CaptureControls from '@/components/dashboard/CaptureControls.vue'
import VolumeMeter from '@/components/dashboard/VolumeMeter.vue'
import VerdictDisplay from '@/components/dashboard/VerdictDisplay.vue'
import LiveLog from '@/components/dashboard/LiveLog.vue'
import StatsRow from '@/components/dashboard/StatsRow.vue'
import ActivityChart from '@/components/dashboard/ActivityChart.vue'
import LiveHistoryTable from '@/components/dashboard/LiveHistoryTable.vue'

// Scenario B: paid users get everything. user comes from AppLayout (GET /api/users/me).
const props = defineProps({
  user: { type: Object, required: true },
  updateQuota: { type: Function, required: true },
})

const router = useRouter()

const {
  isListening,
  currentResult,
  liveLogs,
  history: liveHistory,
  devices,
  selectedDevice,
  mode,
  chunkSize,
  volume,
  statusText,
  statusWarn,
  errorMessage,
  startCapture,
  stopCapture,
} = useAudioCapture({
  onQuota: props.updateQuota,
  onSessionExpired: () => router.replace('/login'),
})

// Saved sessions from GET /api/history feed the stats row and the weekly chart.
const savedHistory = ref([])

const loadSavedHistory = async () => {
  try {
    const response = await authFetch('/api/history')
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)
    const data = await response.json()
    savedHistory.value = Array.isArray(data) ? data : []
  } catch {
    savedHistory.value = []
  }
}

const summary = computed(() => summarizeHistory(savedHistory.value))
const toggle = () => (isListening.value ? stopCapture() : startCapture())
const buttonText = computed(() => (isListening.value ? 'Stop listening' : 'Start listening'))

// A finished session is saved on the server, so reload the saved history when it stops.
watch(isListening, (now, before) => {
  if (before && !now) loadSavedHistory()
})

onMounted(loadSavedHistory)
</script>

<template>
  <div class="flex flex-col gap-5">
    <p
      v-if="errorMessage"
      class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <!-- Top row: controls on the left, result and developer log on the right -->
    <div class="grid gap-5 xl:grid-cols-12">
      <section class="flex flex-col gap-6 rounded-3xl border border-back-secondary bg-back-secondary/40 p-6 xl:col-span-5">
        <div class="flex items-center gap-5">
          <PlayButton size="sm" :playing="isListening" :pulse="isListening" :label="buttonText" @click="toggle" />
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold">{{ buttonText }}</p>
            <VolumeMeter :volume="volume" class="mt-3" />
          </div>
        </div>

        <CaptureControls
          v-model:mode="mode"
          v-model:selected-device="selectedDevice"
          v-model:chunk-size="chunkSize"
          :devices="devices"
          :locked="isListening"
        />
      </section>

      <div class="flex flex-col gap-5 xl:col-span-7">
        <section class="rounded-3xl border border-back-secondary bg-gradient-to-br from-back-secondary to-back-prime px-6 py-8">
          <VerdictDisplay
            :result="currentResult"
            :listening="isListening"
            :status-text="statusText"
            :status-warn="statusWarn"
          />
        </section>

        <LiveLog :logs="liveLogs" :listening="isListening" />
      </div>
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
      <ActivityChart class="xl:col-span-1" :history="savedHistory" />
      <LiveHistoryTable class="xl:col-span-2" :rows="liveHistory" />
    </div>
  </div>
</template>
