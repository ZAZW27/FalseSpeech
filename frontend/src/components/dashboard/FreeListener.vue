<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAudioCapture } from '@/assets/js/useAudioCapture'
import PlayButton from '@/components/ui/buttons/PlayButton.vue'
import CaptureControls from '@/components/dashboard/CaptureControls.vue'
import VerdictDisplay from '@/components/dashboard/VerdictDisplay.vue'
import AudioProbeModal from '@/components/ui/modals/AudioProbeModal.vue'

// Scenario A: free users get the controls, the play button and the verdict only.
const props = defineProps({
  user: { type: Object, required: true },
  updateQuota: { type: Function, required: true },
})

const route = useRoute()
const router = useRouter()

const {
  isListening,
  currentResult,
  devices,
  verifiedDevices,
  markVerifiedDevices,
  selectedDevice,
  mode,
  chunkSize,
  statusText,
  statusWarn,
  errorMessage,
  refreshDevices,
  startCapture,
  stopCapture,
} = useAudioCapture({
  onQuota: props.updateQuota,
  onSessionExpired: () => router.replace('/login'),
})

const probeOpen = ref(false)
const onAudioDetected = ({ bestDeviceId, activeDeviceIds }) => {
  markVerifiedDevices(activeDeviceIds)
  mode.value = 'monitor'
  selectedDevice.value = bestDeviceId
}

const toggle = () => (isListening.value ? stopCapture() : startCapture())

onMounted(() => {
  if (route.query.autostart === '1') {
    router.replace({ path: '/dashboard', query: {} })
    startCapture()
  }
})
</script>

<template>
  <div class="mx-auto flex max-w-[620px] flex-col items-center gap-10 py-6">
    <PlayButton
      size="xl"
      :playing="isListening"
      :pulse="isListening"
      :label="isListening ? 'Stop listening' : 'Start listening'"
      @click="toggle"
    />

    <VerdictDisplay
      :result="currentResult"
      :listening="isListening"
      :status-text="statusText"
      :status-warn="statusWarn"
      size="xl"
    />

    <p
      v-if="errorMessage"
      class="max-w-[420px] rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-center text-sm text-red-400"
      role="alert"
    >
      {{ errorMessage }}
    </p>

    <section class="w-full rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-6">
      <div class="mb-4 flex items-center justify-between gap-2">
        <span class="text-xs font-semibold uppercase tracking-wider text-secondary/70">Audio Setup</span>
        <button
          type="button"
          :disabled="isListening"
          class="rounded-lg border border-brand-green/50 bg-[#2f6b5e]/80 px-2.5 py-1 text-[11px] font-bold text-white transition hover:bg-[#2f6b5e] disabled:opacity-40"
          @click="probeOpen = true"
        >
          Auto-Detect
        </button>
      </div>
      <CaptureControls
        v-model:mode="mode"
        v-model:selected-device="selectedDevice"
        v-model:chunk-size="chunkSize"
        :devices="devices"
        :verified-devices="verifiedDevices"
        :locked="isListening"
      />
    </section>

    <AudioProbeModal
      v-model="probeOpen"
      :devices="devices"
      :refresh-devices="refreshDevices"
      @detected="onAudioDetected"
      @switch-tab-mode="mode = 'tab'"
    />
  </div>
</template>
