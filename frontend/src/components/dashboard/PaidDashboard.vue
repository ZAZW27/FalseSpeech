<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
import AudioProbeModal from '@/components/ui/modals/AudioProbeModal.vue'
import DashboardTutorial from '@/components/dashboard/DashboardTutorial.vue'

// Scenario B: paid users get everything. user comes from AppLayout (GET /api/users/me).
const props = defineProps({
  user: { type: Object, required: true },
  updateQuota: { type: Function, required: true },
})

const route = useRoute()
const router = useRouter()

const {
  isListening,
  currentResult,
  liveLogs,
  history: liveHistory,
  devices,
  verifiedDevices,
  markVerifiedDevices,
  selectedDevice,
  mode,
  chunkSize,
  volume,
  statusText,
  statusWarn,
  errorMessage,
  fairUsageExceeded,
  refreshDevices,
  startCapture,
  stopCapture,
} = useAudioCapture({
  onQuota: props.updateQuota,
  onSessionExpired: () => router.replace('/login'),
})

const probeOpen = ref(false)
const showTerminal = ref(
  (() => {
    try {
      return localStorage.getItem('fs_pref_show_terminal') === 'true'
    } catch {
      return false
    }
  })(),
)

const toggleTerminal = () => {
  showTerminal.value = !showTerminal.value
  try {
    localStorage.setItem('fs_pref_show_terminal', String(showTerminal.value))
  } catch {}
}

const onAudioDetected = ({ bestDeviceId, activeDeviceIds }) => {
  markVerifiedDevices(activeDeviceIds)
  if (bestDeviceId) {
    mode.value = 'monitor'
    selectedDevice.value = bestDeviceId
  }
}

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

onMounted(() => {
  loadSavedHistory()
  if (route.query.autostart === '1') {
    router.replace({ path: '/dashboard', query: {} })
    startCapture()
  }
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- UC-12: Dedicated red Fair Usage Policy (FUP) alert banner for Lifetime users -->
    <div
      v-if="fairUsageExceeded"
      class="flex flex-col gap-1 rounded-2xl border-2 border-red-500/60 bg-red-500/15 px-5 py-4 text-red-200 shadow-lg"
      role="alert"
    >
      <p class="text-sm font-bold uppercase tracking-wider text-red-400">
        Fair Usage Policy (12-Hour Daily Limit Reached)
      </p>
      <p class="text-sm text-red-200/90">
        {{ errorMessage || 'Lifetime accounts are limited to 12 hours (43,200 seconds) of continuous listening per day. Your quota will automatically reset at midnight UTC.' }}
      </p>
    </div>

    <p
      v-else-if="errorMessage"
      class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <!-- Top row: controls on the left, result and developer log on the right -->
    <div class="grid gap-5 xl:grid-cols-12">
      <section class="flex flex-col gap-6 rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6 xl:col-span-5">
        <div data-tour="play-control" class="flex items-center gap-5">
          <PlayButton size="sm" :playing="isListening" :pulse="isListening" :label="buttonText" @click="toggle" />
          <div class="min-w-0 flex-1">
            <div class="flex items-center justify-between gap-2">
              <p class="text-sm font-semibold">{{ buttonText }}</p>
              <button
                data-tour="auto-detect"
                type="button"
                :disabled="isListening"
                class="rounded-lg border border-brand-green/50 bg-[#2f6b5e]/80 px-2.5 py-1 text-[11px] font-bold text-white transition hover:bg-[#2f6b5e] disabled:opacity-40"
                @click="probeOpen = true"
              >
                Auto-Detect
              </button>
            </div>
            <VolumeMeter :volume="volume" class="mt-3" />
          </div>
        </div>

        <div data-tour="capture-controls">
          <CaptureControls
            v-model:mode="mode"
            v-model:selected-device="selectedDevice"
            v-model:chunk-size="chunkSize"
            :devices="devices"
            :verified-devices="verifiedDevices"
            :locked="isListening"
          />
        </div>

        <AudioProbeModal
          v-model="probeOpen"
          :devices="devices"
          :refresh-devices="refreshDevices"
          @detected="onAudioDetected"
          @switch-tab-mode="mode = 'tab'"
        />
      </section>

      <div class="flex flex-col xl:col-span-7">
        <section
          data-tour="verdict-panel"
          class="relative flex flex-1 flex-col justify-center rounded-3xl border-2 border-back-secondary bg-gradient-to-br from-back-secondary to-back-prime px-6 py-8 transition-all duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]"
        >
          <button
            data-tour="terminal-toggle"
            type="button"
            class="absolute right-4 top-4 rounded-lg border border-white/15 bg-back-prime/70 px-2.5 py-1 font-mono text-[11px] font-semibold text-secondary/80 transition hover:border-brand-green/60 hover:text-brand-green"
            @click="toggleTerminal"
          >
            {{ showTerminal ? 'Hide Terminal' : 'Show Terminal' }}
          </button>

          <VerdictDisplay
            :result="currentResult"
            :listening="isListening"
            :status-text="statusText"
            :status-warn="statusWarn"
          />
        </section>

        <!-- Smooth grid-row expansion + CRT TV scanline transition -->
        <div
          :class="[
            'grid transition-[grid-template-rows,margin-top,opacity] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]',
            showTerminal ? 'mt-5 grid-rows-[1fr] opacity-100' : 'mt-0 grid-rows-[0fr] opacity-0 pointer-events-none',
          ]"
        >
          <div class="overflow-hidden">
            <div :class="showTerminal ? 'crt-screen-on' : 'crt-screen-off'">
              <LiveLog :logs="liveLogs" :listening="isListening" />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Middle row -->
    <div data-tour="stats-row">
      <StatsRow
        :used-seconds="user.quota_used"
        :limit-seconds="user.quota_limit"
        :total="summary.total"
        :ai="summary.ai"
        :human="summary.human"
      />
    </div>

    <!-- Bottom row -->
    <div class="grid gap-5 xl:grid-cols-3">
      <ActivityChart class="xl:col-span-1" :history="savedHistory" />
      <LiveHistoryTable class="xl:col-span-2" :rows="liveHistory" />
    </div>

    <DashboardTutorial />
  </div>
</template>
