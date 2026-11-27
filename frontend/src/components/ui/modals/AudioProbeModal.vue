<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import BaseModal from '@/components/ui/modals/BaseModal.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'

const PROBE_AUDIO_URL = '/audio/probe-chime.wav'
const PROBE_MS = 900
const ACTIVE_PEAK_THRESHOLD = 4

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  devices: { type: Array, default: () => [] },
  refreshDevices: { type: Function, required: true },
})

const emit = defineEmits(['update:modelValue', 'detected', 'switch-tab-mode'])

// Per-device scan results: { deviceId, label, kind: 'internal'|'external', status, peak }
const rows = ref([])
const isScanning = ref(false)
const scanDone = ref(false)
const selectedDriverId = ref('')
const isPlayingTone = ref(false)
let cancelScan = false
let probeAudio = null
let fadeRaf = null

const isInternalDriver = (label) => {
  const s = String(label || '').toLowerCase()
  if (/monitor|loopback|stereo mix|what u hear|blackhole|soundflower|virtual cable|vb-audio/i.test(s)) {
    return true
  }
  return false
}

const activeInternalRows = computed(() => rows.value.filter((r) => r.status === 'active' && r.kind === 'internal'))
const activeExternalRows = computed(() => rows.value.filter((r) => r.status === 'active' && r.kind === 'external'))
const noInternalDetected = computed(() => scanDone.value && activeInternalRows.value.length === 0)
const selectedRow = computed(() => rows.value.find((r) => r.deviceId === selectedDriverId.value) || null)

const startTestTone = async () => {
  stopTestTone(true)
  try {
    probeAudio = new Audio(PROBE_AUDIO_URL)
    probeAudio.loop = true
    probeAudio.volume = 0.55
    await probeAudio.play()
    isPlayingTone.value = true
  } catch {
    isPlayingTone.value = false
  }
}

const stopTestTone = (immediate = false) => {
  if (fadeRaf) {
    cancelAnimationFrame(fadeRaf)
    fadeRaf = null
  }
  const audio = probeAudio
  probeAudio = null
  isPlayingTone.value = false
  if (!audio) return

  if (immediate || audio.paused || audio.volume <= 0.01) {
    try {
      audio.pause()
      audio.currentTime = 0
    } catch {}
    return
  }

  // Smooth exponential fade-out into silence (~950ms) so the chime dissolves softly into the void
  const startVol = audio.volume
  const fadeMs = 950
  const started = performance.now()
  const step = (now) => {
    const progress = Math.min(1, (now - started) / fadeMs)
    const eased = Math.pow(1 - progress, 2.2)
    try {
      audio.volume = Math.max(0, startVol * eased)
    } catch {}
    if (progress < 1) {
      fadeRaf = requestAnimationFrame(step)
    } else {
      fadeRaf = null
      try {
        audio.pause()
        audio.currentTime = 0
      } catch {}
    }
  }
  fadeRaf = requestAnimationFrame(step)
}

const probeSingleDevice = async (deviceId) => {
  const Context = window.AudioContext || window.webkitAudioContext
  let stream = null
  let ctx = null
  try {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: deviceId },
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      })
    } catch {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { deviceId } })
    }

    if (!Context) return { status: 'silent', peak: 0 }
    ctx = new Context()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 256
    const src = ctx.createMediaStreamSource(stream)
    src.connect(analyser)

    const buf = new Uint8Array(analyser.frequencyBinCount)
    let peak = 0
    const started = performance.now()

    while (performance.now() - started < PROBE_MS && !cancelScan) {
      analyser.getByteFrequencyData(buf)
      let sum = 0
      for (let i = 0; i < buf.length; i++) sum += buf[i]
      const level = Math.min(100, Math.round((sum / buf.length / 128) * 100 * 2))
      if (level > peak) peak = level
      await new Promise((r) => setTimeout(r, 50))
    }

    return { status: peak >= ACTIVE_PEAK_THRESHOLD ? 'active' : 'silent', peak }
  } catch {
    return { status: 'error', peak: 0 }
  } finally {
    stream?.getTracks().forEach((t) => t.stop())
    ctx?.close().catch(() => {})
  }
}

const prepareDeviceList = async () => {
  await props.refreshDevices()
  rows.value = props.devices.map((d) => ({
    deviceId: d.deviceId,
    label: d.label,
    kind: isInternalDriver(d.label) ? 'internal' : 'external',
    status: 'pending',
    peak: 0,
  }))
}

const runScan = async () => {
  if (isScanning.value) return
  cancelScan = false
  isScanning.value = true
  scanDone.value = false
  selectedDriverId.value = ''

  await prepareDeviceList()
  if (cancelScan) {
    isScanning.value = false
    return
  }

  // Play a gentle, soothing chime through system output so loopback/monitor drivers light up automatically
  await startTestTone()
  // Brief head-start so the chime fade-in reaches the audio pipeline before probing the first driver
  await new Promise((r) => setTimeout(r, 250))

  const activeRows = []
  for (let i = 0; i < rows.value.length; i++) {
    if (cancelScan) break
    rows.value[i].status = 'scanning'
    const res = await probeSingleDevice(rows.value[i].deviceId)
    if (cancelScan) break
    rows.value[i].status = res.status
    rows.value[i].peak = res.peak
    if (res.status === 'active') activeRows.push(rows.value[i])
  }

  stopTestTone()
  isScanning.value = false
  if (cancelScan) return
  scanDone.value = true

  // Mark every active driver immediately so the Audio Input dropdown shows the verified dot even without clicking
  const allActiveIds = activeRows.map((r) => r.deviceId)
  const internals = activeRows.filter((r) => r.kind === 'internal').sort((a, b) => b.peak - a.peak)
  if (internals.length > 0) {
    selectedDriverId.value = internals[0].deviceId
  }
  if (allActiveIds.length > 0) {
    emit('detected', {
      bestDeviceId: internals[0]?.deviceId ?? null,
      activeDeviceIds: allActiveIds,
    })
  }
}

const pickDriver = (row) => {
  if (isScanning.value) return
  selectedDriverId.value = row.deviceId
  const activeIds = rows.value.filter((r) => r.status === 'active').map((r) => r.deviceId)
  if (!activeIds.includes(row.deviceId)) activeIds.push(row.deviceId)
  emit('detected', {
    bestDeviceId: row.deviceId,
    activeDeviceIds: activeIds,
  })
}

const close = () => {
  cancelScan = true
  isScanning.value = false
  stopTestTone()
  emit('update:modelValue', false)
}

const useTabShare = () => {
  cancelScan = true
  isScanning.value = false
  stopTestTone()
  emit('switch-tab-mode')
  emit('update:modelValue', false)
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      scanDone.value = false
      selectedDriverId.value = ''
      prepareDeviceList()
    } else {
      cancelScan = true
      isScanning.value = false
      stopTestTone()
    }
  },
)

onBeforeUnmount(stopTestTone)
</script>

<template>
  <BaseModal :model-value="modelValue" label="Auto-detect audio driver" transition="crt" @update:model-value="close">
    <div class="rounded-t-3xl border-2 border-back-secondary bg-back-prime p-6 text-slate-100 sm:p-7 md:rounded-3xl">
      <div>
        <h2 class="text-xl font-extrabold text-slate-100">Auto-Detect Audio Input</h2>
        <p class="mt-1 text-xs leading-relaxed text-slate-400">
          Tests every audio driver on your computer to separate <strong class="text-slate-200">Internal (System)</strong>
          audio from <strong class="text-slate-200">External (Microphone)</strong> inputs.
        </p>
      </div>

      <!-- Sound Warning Banner (shown before scan starts) -->
      <div
        v-if="!isScanning && !scanDone"
        class="mt-4 rounded-2xl border border-amber-400/35 bg-amber-400/10 px-4 py-3 text-xs leading-relaxed text-amber-100"
      >
        <p class="font-bold text-amber-200">Sound Notice</p>
        <p class="mt-0.5 text-amber-100/90">
          Clicking <strong>Start Scan</strong> will play a sound to help detect working internal drivers.
        </p>
      </div>

      <!-- Playing Chime Status -->
      <div
        v-if="isScanning"
        class="mt-4 flex items-center justify-between rounded-2xl border border-white/15 bg-white/5 px-4 py-2.5 text-xs text-slate-200"
      >
        <span>
          {{ isPlayingTone ? 'Playing calm test chime and scanning drivers...' : 'Scanning audio drivers...' }}
        </span>
        <span class="text-[11px] font-medium text-slate-400">Please wait</span>
      </div>

      <!-- Drivers List -->
      <div class="mt-4 flex max-h-[290px] flex-col gap-2 overflow-y-auto pr-1">
        <p v-if="!rows.length && !isScanning" class="rounded-2xl border border-white/10 p-4 text-center text-xs text-slate-400">
          No audio input drivers exposed by this browser. Use Tab / System Share below.
        </p>

        <button
          v-for="row in rows"
          :key="row.deviceId"
          type="button"
          :disabled="isScanning"
          :class="[
            'flex w-full items-center justify-between gap-3 rounded-2xl border-2 px-4 py-3 text-left text-xs transition',
            selectedDriverId === row.deviceId
              ? 'border-brand-green/80 bg-white/[0.06] text-slate-100'
              : row.status === 'active'
                ? 'border-white/25 bg-white/[0.04] text-slate-100 hover:border-white/40'
                : row.status === 'scanning'
                  ? 'border-sky-400/50 bg-sky-400/10 text-slate-100'
                  : 'border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20',
          ]"
          @click="pickDriver(row)"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <p class="truncate font-semibold text-slate-100">{{ row.label }}</p>
              <span
                :class="[
                  'shrink-0 rounded-md border px-1.5 py-0.5 text-[10px] font-semibold',
                  row.kind === 'internal'
                    ? 'border-white/20 text-slate-200'
                    : 'border-white/10 text-slate-400',
                ]"
              >
                {{ row.kind === 'internal' ? 'Internal' : 'External Mic' }}
              </span>
            </div>
            <div class="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
              <div
                :class="[
                  'h-full rounded-full transition-all duration-150',
                  row.status === 'active' ? 'bg-brand-green' : row.status === 'scanning' ? 'bg-sky-400 animate-pulse' : 'bg-white/20',
                ]"
                :style="{ width: row.status === 'scanning' ? '55%' : `${Math.max(4, row.peak)}%` }"
              />
            </div>
          </div>

          <span class="shrink-0 text-[11px] font-semibold text-slate-300">
            <template v-if="selectedDriverId === row.deviceId">
              <span class="text-brand-green">● Selected</span>
            </template>
            <template v-else-if="row.status === 'active'">
              <span class="text-slate-100">Active ({{ row.peak }}%)</span>
            </template>
            <template v-else-if="row.status === 'scanning'">
              <span class="text-sky-300">Testing...</span>
            </template>
            <template v-else-if="row.status === 'error'">
              <span class="text-red-300">Blocked</span>
            </template>
            <template v-else-if="row.status === 'silent'">
              <span class="text-slate-500">Silent</span>
            </template>
            <template v-else>
              <span class="text-slate-500">Ready</span>
            </template>
          </span>
        </button>
      </div>

      <!-- Result Banner: Internal System Sound Found -->
      <div
        v-if="scanDone && activeInternalRows.length > 0"
        class="mt-4 rounded-2xl border border-white/15 bg-white/[0.04] px-4 py-3 text-xs text-slate-200"
      >
        <p class="font-semibold text-slate-100">
          Detected {{ activeInternalRows.length }} internal system driver{{ activeInternalRows.length === 1 ? '' : 's' }}
          <span v-if="activeExternalRows.length" class="font-normal text-slate-400">
            (ignored {{ activeExternalRows.length }} external mic{{ activeExternalRows.length === 1 ? '' : 's' }})
          </span>
        </p>
        <p v-if="selectedRow" class="mt-0.5 text-slate-400">
          Selected: <strong class="text-slate-200">{{ selectedRow.label }}</strong>. You can also click any driver above to choose it, then click Close.
        </p>
      </div>

      <!-- Result Banner: No Internal Sound Detected -->
      <div
        v-if="noInternalDetected"
        class="mt-4 rounded-2xl border border-amber-400/35 bg-amber-400/10 px-4 py-3 text-xs leading-relaxed text-amber-100"
        role="alert"
      >
        <p class="font-bold text-amber-200">No internal system sound detected.</p>
        <p class="mt-0.5 text-amber-100/90">
          {{
            activeExternalRows.length
              ? 'Only an external microphone picked up sound. Check that your headphones/speaker output is active, or play an audio/video clip and click Scan Again.'
              : 'All drivers were silent. Make sure your system output is unmuted, play an audio/video clip and click Scan Again, or use Mode B: Tab / System Share.'
          }}
        </p>
      </div>

      <!-- Footer (never auto-closes; user clicks Close when done) -->
      <div class="mt-6 flex flex-wrap items-center justify-end gap-2.5">
        <BaseButton size="sm" variant="outlineLight" @click="useTabShare">
          Use Tab / System Share
        </BaseButton>
        <button
          v-if="!isScanning"
          type="button"
          class="rounded-xl bg-gradient-to-r from-[#b7d894] via-[#c3e2a2] to-[#a7cb82] px-4 py-2 text-xs font-bold text-back-prime shadow-sm transition hover:brightness-105"
          @click="runScan"
        >
          {{ scanDone ? 'Scan Again' : 'Start Scan' }}
        </button>
        <BaseButton size="sm" variant="ghost" @click="close">
          {{ scanDone ? 'Done' : 'Close' }}
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>
