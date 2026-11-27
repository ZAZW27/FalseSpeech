<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { authFetch } from '@/assets/js/api'

const TARGET_SR = 16000
const DIARIZE_SR = 8000

const CLIP_COLORS = [
  'rgba(183, 216, 148, 0.30)',
  'rgba(96, 165, 250, 0.30)',
  'rgba(244, 114, 182, 0.30)',
  'rgba(251, 191, 36, 0.30)',
  'rgba(167, 139, 250, 0.30)',
]

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const chunkSize = defineModel('chunkSize', { type: Number, default: 5 })
const emit = defineEmits(['chunk-result', 'session-complete', 'log', 'error'])

const fileInputRef = ref(null)
const canvasRef = ref(null)

const audioFile = ref(null)
const audioUrl = ref('')
const duration = ref(0)
const currentTime = ref(0)
const isPlaying = ref(false)
const isDraggingFile = ref(false)
const isDecoding = ref(false)
const isDiarizing = ref(false)
const isAnalyzing = ref(false)
const progressText = ref('')
const progressPct = ref(0)
const sessionTitle = ref('')
const localError = ref('')

// Manual & Auto multi-speaker editing mode
const editMode = ref(false)
const clips = ref([]) // [{ id, label, start_s, end_s, color }]
const draftStart = ref(0)
const draftEnd = ref(0)
const draftLabel = ref('')
const isSelectingWave = ref(false)
const selectAnchorS = ref(0)

let audioEl = null
let pcm16kMono = null // Float32Array kept in client RAM at 16kHz mono (strips stereo/video/ultrasonic waste losslessly for Wav2Vec2)
let peaks = []
let clipStopTime = null
let clipIdCounter = 0
let cancelAnalysis = false

const formatSec = (s) => {
  const sec = Math.max(0, Number(s) || 0)
  const m = Math.floor(sec / 60)
  const r = (sec % 60).toFixed(1).padStart(4, '0')
  return `${String(m).padStart(2, '0')}:${r}`
}

const formatBytes = (b) => {
  if (b >= 1024 * 1024 * 1024) return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`
  if (b >= 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(1)} MB`
  return `${Math.max(1, Math.round(b / 1024))} KB`
}

const hasValidDraft = computed(() => draftEnd.value - draftStart.value >= 0.5)

// Mixes multi-channel AudioBuffer to mono and resamples to target sample rate in client RAM
const resampleBufferToMono = (audioBuffer, outSr) => {
  const inSr = audioBuffer.sampleRate
  const inLen = audioBuffer.length
  const channels = audioBuffer.numberOfChannels

  const mono = new Float32Array(inLen)
  for (let c = 0; c < channels; c++) {
    const chData = audioBuffer.getChannelData(c)
    for (let i = 0; i < inLen; i++) mono[i] += chData[i] / channels
  }

  if (inSr === outSr) return mono

  const outLen = Math.max(1, Math.round((inLen * outSr) / inSr))
  const out = new Float32Array(outLen)
  const ratio = inSr / outSr
  for (let i = 0; i < outLen; i++) {
    const srcPos = i * ratio
    const idx = Math.floor(srcPos)
    const frac = srcPos - idx
    const s0 = mono[idx] ?? 0
    const s1 = mono[Math.min(inLen - 1, idx + 1)] ?? s0
    out[i] = s0 + (s1 - s0) * frac
  }
  return out
}

// Encodes a Float32Array mono slice into a clean 16-bit PCM WAV Blob (lossless for Wav2Vec2 16kHz)
const encodePcmToWavBlob = (samples, sampleRate) => {
  const numSamples = samples.length
  const buffer = new ArrayBuffer(44 + numSamples * 2)
  const view = new DataView(buffer)

  const writeStr = (offset, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }

  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + numSamples * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // Mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, numSamples * 2, true)

  let offset = 44
  for (let i = 0; i < numSamples; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

const downsample16kTo8k = (samples16k) => {
  const outLen = Math.max(1, Math.floor(samples16k.length / 2))
  const out = new Float32Array(outLen)
  for (let i = 0; i < outLen; i++) {
    out[i] = 0.5 * ((samples16k[i * 2] ?? 0) + (samples16k[i * 2 + 1] ?? 0))
  }
  return out
}

const drawWaveform = () => {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const w = canvas.width
  const h = canvas.height
  ctx.clearRect(0, 0, w, h)

  ctx.fillStyle = '#141923'
  ctx.fillRect(0, 0, w, h)

  if (duration.value > 0) {
    for (const c of clips.value) {
      const x1 = (c.start_s / duration.value) * w
      const x2 = (c.end_s / duration.value) * w
      ctx.fillStyle = c.color
      ctx.fillRect(x1, 0, Math.max(2, x2 - x1), h)
      ctx.strokeStyle = 'rgba(255,255,255,0.45)'
      ctx.lineWidth = 1
      ctx.strokeRect(x1 + 0.5, 0.5, Math.max(1, x2 - x1 - 1), h - 1)
    }

    if (editMode.value && draftEnd.value > draftStart.value) {
      const x1 = (draftStart.value / duration.value) * w
      const x2 = (draftEnd.value / duration.value) * w
      ctx.fillStyle = 'rgba(183, 216, 148, 0.22)'
      ctx.fillRect(x1, 0, Math.max(2, x2 - x1), h)
      ctx.strokeStyle = '#B7D894'
      ctx.lineWidth = 2
      ctx.strokeRect(x1 + 1, 1, Math.max(1, x2 - x1 - 2), h - 2)
    }
  }

  if (peaks.length) {
    const barW = w / peaks.length
    for (let i = 0; i < peaks.length; i++) {
      const amp = Math.max(0.06, peaks[i])
      const barH = amp * (h * 0.82)
      const x = i * barW
      const y = (h - barH) / 2
      const progress = duration.value > 0 ? currentTime.value / duration.value : 0
      ctx.fillStyle = i / peaks.length <= progress ? '#B7D894' : 'rgba(226, 232, 240, 0.35)'
      ctx.fillRect(x, y, Math.max(1.5, barW - 1), barH)
    }
  }

  if (duration.value > 0) {
    const px = (currentTime.value / duration.value) * w
    ctx.fillStyle = '#f8fafc'
    ctx.fillRect(px - 1, 0, 2, h)
  }
}

const cleanupAudio = () => {
  cancelAnalysis = true
  if (audioEl) {
    audioEl.pause()
    audioEl.src = ''
    audioEl = null
  }
  if (audioUrl.value) {
    URL.revokeObjectURL(audioUrl.value)
    audioUrl.value = ''
  }
  pcm16kMono = null
  isPlaying.value = false
  clipStopTime = null
}

const loadFile = async (file) => {
  if (!file) return
  localError.value = ''
  cleanupAudio()
  isDecoding.value = true

  audioFile.value = file
  sessionTitle.value = file.name.replace(/\.[^.]+$/, '')
  clips.value = []
  draftStart.value = 0
  draftEnd.value = 0
  draftLabel.value = ''
  currentTime.value = 0
  duration.value = 0
  peaks = []

  audioUrl.value = URL.createObjectURL(file)
  audioEl = new Audio(audioUrl.value)
  audioEl.addEventListener('timeupdate', () => {
    if (!audioEl) return
    currentTime.value = audioEl.currentTime
    if (clipStopTime !== null && audioEl.currentTime >= clipStopTime) {
      audioEl.pause()
      isPlaying.value = false
      clipStopTime = null
    }
    drawWaveform()
  })
  audioEl.addEventListener('ended', () => {
    isPlaying.value = false
    clipStopTime = null
    drawWaveform()
  })

  try {
    const Context = window.AudioContext || window.webkitAudioContext
    if (!Context) throw new Error('Web Audio API unavailable in this browser.')
    const arrayBuf = await file.arrayBuffer()
    const ctx = new Context()
    const decoded = await ctx.decodeAudioData(arrayBuf)
    duration.value = decoded.duration

    // Compress in client RAM to lossless 16kHz mono (strips stereo/video/ultrasonic waste without hurting Wav2Vec2)
    pcm16kMono = resampleBufferToMono(decoded, TARGET_SR)
    ctx.close().catch(() => {})

    const bars = 120
    const step = Math.max(1, Math.floor(pcm16kMono.length / bars))
    const computedPeaks = []
    for (let i = 0; i < bars; i++) {
      let max = 0
      const start = i * step
      const end = Math.min(pcm16kMono.length, start + step)
      for (let j = start; j < end; j++) {
        const v = Math.abs(pcm16kMono[j])
        if (v > max) max = v
      }
      computedPeaks.push(max)
    }
    const norm = Math.max(0.01, ...computedPeaks)
    peaks = computedPeaks.map((p) => p / norm)

    draftStart.value = 0
    draftEnd.value = Math.min(duration.value, 5)
    emit(
      'log',
      `cached locally: ${file.name} (${formatBytes(file.size)} -> ${formatBytes(pcm16kMono.length * 2)} 16kHz mono PCM, ${duration.value.toFixed(1)}s)`,
    )
  } catch (err) {
    localError.value = `Could not decode audio in browser: ${err?.message || 'unsupported format'}`
    emit('error', localError.value)
  } finally {
    isDecoding.value = false
    await nextTick()
    drawWaveform()
  }
}

const onFileInput = (e) => {
  const file = e.target?.files?.[0]
  if (file) loadFile(file)
  if (e.target) e.target.value = ''
}

const onDrop = (e) => {
  isDraggingFile.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) loadFile(file)
}

const togglePlay = () => {
  if (!audioEl) return
  clipStopTime = null
  if (isPlaying.value) {
    audioEl.pause()
    isPlaying.value = false
  } else {
    audioEl.play().catch(() => {})
    isPlaying.value = true
  }
}

const playClipRange = (startS, endS) => {
  if (!audioEl) return
  audioEl.currentTime = startS
  clipStopTime = endS
  audioEl.play().catch(() => {})
  isPlaying.value = true
}

const timeFromPointer = (e) => {
  const canvas = canvasRef.value
  if (!canvas || !duration.value) return 0
  const rect = canvas.getBoundingClientRect()
  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
  return Number((ratio * duration.value).toFixed(2))
}

const onWaveDown = (e) => {
  if (!duration.value) return
  const t = timeFromPointer(e)
  if (editMode.value) {
    isSelectingWave.value = true
    selectAnchorS.value = t
    draftStart.value = t
    draftEnd.value = t
    drawWaveform()
  } else if (audioEl) {
    audioEl.currentTime = t
    currentTime.value = t
    drawWaveform()
  }
}

const onWaveMove = (e) => {
  if (!isSelectingWave.value || !editMode.value) return
  const t = timeFromPointer(e)
  draftStart.value = Math.min(selectAnchorS.value, t)
  draftEnd.value = Math.max(selectAnchorS.value, t)
  drawWaveform()
}

const onWaveUp = () => {
  isSelectingWave.value = false
}

const addClip = () => {
  if (!hasValidDraft.value) return
  const idx = clips.value.length + 1
  const label = draftLabel.value.trim() || `Speaker ${idx}`
  clips.value.push({
    id: ++clipIdCounter,
    label,
    start_s: Number(draftStart.value.toFixed(2)),
    end_s: Number(draftEnd.value.toFixed(2)),
    color: CLIP_COLORS[(idx - 1) % CLIP_COLORS.length],
  })
  draftLabel.value = ''
  drawWaveform()
}

const removeClip = (id) => {
  clips.value = clips.value.filter((c) => c.id !== id)
  drawWaveform()
}

const clearFile = () => {
  cleanupAudio()
  audioFile.value = null
  sessionTitle.value = ''
  clips.value = []
  duration.value = 0
  currentTime.value = 0
  peaks = []
  localError.value = ''
  progressText.value = ''
  progressPct.value = 0
}

// Stage 1: Automatic Speaker Diarization (Silero VAD + MFCC clustering on compressed 8kHz mono audio)
const autoDetectSpeakers = async () => {
  if (!pcm16kMono || isDiarizing.value || isAnalyzing.value) return
  isDiarizing.value = true
  localError.value = ''
  emit('log', 'running Silero VAD speaker diarization on compressed 8kHz mono audio...')

  try {
    const pcm8k = downsample16kTo8k(pcm16kMono)
    const compressedBlob = encodePcmToWavBlob(pcm8k, DIARIZE_SR)

    const fd = new FormData()
    fd.append('file', compressedBlob, 'diarize_8k.wav')
    fd.append('max_speakers', '4')

    const res = await authFetch('/api/detect/diarize', {
      method: 'POST',
      body: fd,
    })
    if (!res.ok) {
      let detail = `Speaker detection failed (${res.status})`
      try {
        const body = await res.json()
        if (body?.detail) detail = body.detail
      } catch {}
      throw new Error(detail)
    }

    const data = await res.json()
    const segs = Array.isArray(data?.segments) ? data.segments : []
    const colorMap = new Map()
    let colorIdx = 0

    clips.value = segs.map((s) => {
      if (!colorMap.has(s.label)) {
        colorMap.set(s.label, CLIP_COLORS[colorIdx % CLIP_COLORS.length])
        colorIdx += 1
      }
      return {
        id: ++clipIdCounter,
        label: s.label,
        start_s: Number(s.start_s),
        end_s: Number(s.end_s),
        color: colorMap.get(s.label),
      }
    })
    editMode.value = true
    emit('log', `diarization found ${data.speakers_detected} speaker(s) across ${segs.length} turn(s)`)
    drawWaveform()
  } catch (err) {
    localError.value = err?.message || 'Could not auto-detect speakers.'
    emit('error', localError.value)
  } finally {
    isDiarizing.value = false
  }
}

// Stage 2: Client-side 16kHz mono chunked streaming (handles 1GB+ Zoom/Meet files without server upload bloat!)
const analyzeRecording = async () => {
  if (!pcm16kMono || isAnalyzing.value || isDiarizing.value) return
  cancelAnalysis = false
  isAnalyzing.value = true
  localError.value = ''
  progressPct.value = 0
  emit('error', '')

  const baseName = sessionTitle.value.trim() || audioFile.value?.name?.replace(/\.[^.]+$/, '') || 'Recorded Audio'

  // Group clips by speaker label so e.g. all "Speaker 1" turns go into one session, and "Speaker 2" into another!
  const targetGroups = []
  if (editMode.value && clips.value.length > 0) {
    const byLabel = new Map()
    for (const c of clips.value) {
      const key = (c.label || 'Speaker 1').trim()
      if (!byLabel.has(key)) byLabel.set(key, [])
      byLabel.get(key).push(c)
    }
    for (const [label, groupClips] of byLabel.entries()) {
      targetGroups.push({ title: `${baseName} - ${label}`, label, ranges: groupClips })
    }
  } else {
    targetGroups.push({
      title: baseName,
      label: 'Full Recording',
      ranges: [{ start_s: 0, end_s: duration.value }],
    })
  }

  // Build exact chunk plan in client RAM
  const safeChunkS = Math.max(1, Math.min(15, Number(chunkSize.value) || 5))
  const chunkSamples = safeChunkS * TARGET_SR
  const minTailSamples = Math.floor(0.6 * TARGET_SR)

  const plan = targetGroups.map((g) => {
    const chunks = []
    for (const r of g.ranges) {
      const sIdx = Math.max(0, Math.round(r.start_s * TARGET_SR))
      const eIdx = Math.min(pcm16kMono.length, Math.round(r.end_s * TARGET_SR))
      if (eIdx - sIdx < Math.floor(0.4 * TARGET_SR)) continue

      let pos = sIdx
      while (pos < eIdx) {
        const nxt = Math.min(eIdx, pos + chunkSamples)
        if (chunks.length && nxt - pos < minTailSamples && chunks[chunks.length - 1].endIdx === pos) {
          chunks[chunks.length - 1].endIdx = nxt
          chunks[chunks.length - 1].endS = nxt / TARGET_SR
        } else {
          chunks.push({ startIdx: pos, endIdx: nxt, startS: pos / TARGET_SR, endS: nxt / TARGET_SR })
        }
        pos = nxt
      }
    }
    return { ...g, chunks }
  })

  const totalChunks = plan.reduce((acc, g) => acc + g.chunks.length, 0)
  if (totalChunks === 0) {
    localError.value = 'Selected audio is too short to analyze (minimum 0.5s).'
    isAnalyzing.value = false
    return
  }

  let completedChunks = 0

  try {
    for (const group of plan) {
      if (cancelAnalysis || !group.chunks.length) continue

      // Create 1 server session for this speaker/recording
      const sessRes = await authFetch('/api/history/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: group.title, source: 'upload' }),
      })
      if (!sessRes.ok) throw new Error(`Could not create session (${sessRes.status})`)
      const createdSess = await sessRes.json()
      const sid = createdSess.session_id

      emit('log', `created session #${sid} (${group.title}) - streaming ${group.chunks.length} chunk(s)...`)

      for (let i = 0; i < group.chunks.length; i++) {
        if (cancelAnalysis) break
        const c = group.chunks[i]
        progressText.value = `${group.label}: Chunk ${i + 1}/${group.chunks.length} (${completedChunks + 1}/${totalChunks})`

        const slice = pcm16kMono.subarray(c.startIdx, c.endIdx)
        const wavBlob = encodePcmToWavBlob(slice, TARGET_SR)

        const fd = new FormData()
        fd.append('file', wavBlob, `chunk_${i + 1}.wav`)
        fd.append('session_id', String(sid))
        fd.append('chunk_index', String(i + 1))
        fd.append('start_s', String(c.startS.toFixed(2)))
        fd.append('end_s', String(c.endS.toFixed(2)))

        const chunkRes = await authFetch('/api/detect/chunk', {
          method: 'POST',
          body: fd,
        })
        if (!chunkRes.ok) {
          let detail = `Chunk analysis failed (${chunkRes.status})`
          try {
            const body = await chunkRes.json()
            if (body?.detail) detail = body.detail
          } catch {}
          throw new Error(detail)
        }

        const result = await chunkRes.json()
        completedChunks += 1
        progressPct.value = Math.round((completedChunks / totalChunks) * 100)
        emit('chunk-result', { ...result, title: group.title, label: group.label })
      }
    }

    if (!cancelAnalysis) {
      progressText.value = `Completed ${completedChunks} chunk(s) across ${plan.length} session(s).`
      emit('session-complete')
    } else {
      progressText.value = 'Analysis cancelled.'
    }
  } catch (err) {
    localError.value = err?.message || 'Could not complete recording analysis.'
    emit('error', localError.value)
  } finally {
    isAnalyzing.value = false
  }
}

const stopAnalysis = () => {
  cancelAnalysis = true
}

watch([draftStart, draftEnd, editMode], () => {
  drawWaveform()
})

onBeforeUnmount(cleanupAudio)
</script>

<template>
  <div class="flex flex-col gap-4">
    <!-- Drop Zone (no 50MB limit: kept in client RAM & streamed as small 16kHz mono chunks) -->
    <div
      v-if="!audioFile"
      :class="[
        'flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-5 py-9 text-center transition',
        isDraggingFile
          ? 'border-brand-green bg-brand-green/10'
          : 'border-white/20 bg-back-prime/50 hover:border-white/35 hover:bg-back-prime/70',
      ]"
      role="button"
      tabindex="0"
      @click="fileInputRef?.click()"
      @keydown.enter.prevent="fileInputRef?.click()"
      @dragover.prevent="isDraggingFile = true"
      @dragleave.prevent="isDraggingFile = false"
      @drop.prevent="onDrop"
    >
      <p class="text-sm font-bold text-slate-100">Drop recorded audio or meeting file here</p>
      <p class="mt-1 text-xs text-slate-400">
        Processed locally in browser RAM and streamed in lightweight 16 kHz chunks (.wav, .mp3, .m4a, .ogg, .webm, .mp4)
      </p>
      <input
        ref="fileInputRef"
        type="file"
        accept="audio/*,video/mp4,video/webm,.wav,.mp3,.m4a,.ogg,.webm,.flac,.mp4"
        class="hidden"
        @change="onFileInput"
      />
    </div>

    <!-- Loaded Recording Editor & Analyzer -->
    <template v-else>
      <div class="flex items-center justify-between gap-2 rounded-xl border border-white/15 bg-back-prime/70 px-3.5 py-2.5">
        <div class="min-w-0">
          <p class="truncate text-xs font-bold text-slate-100">{{ audioFile.name }}</p>
          <p class="text-[11px] tabular-nums text-slate-400">
            {{ isDecoding ? 'Decoding in browser RAM...' : `${formatSec(currentTime)} / ${formatSec(duration)} (${formatBytes(audioFile.size)})` }}
          </p>
        </div>
        <div class="flex items-center gap-2">
          <button
            type="button"
            :disabled="isDecoding"
            class="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-semibold text-slate-100 transition hover:bg-white/15 disabled:opacity-40"
            @click="togglePlay"
          >
            {{ isPlaying ? 'Pause' : 'Play' }}
          </button>
          <button
            type="button"
            :disabled="isAnalyzing || isDiarizing"
            class="rounded-lg border border-white/15 px-2 py-1 text-xs text-slate-400 transition hover:bg-white/10 hover:text-slate-100 disabled:opacity-40"
            @click="clearFile"
          >
            Change
          </button>
        </div>
      </div>

      <!-- Interactive Waveform + Auto-Detect Speakers + Manual Split -->
      <div>
        <div class="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <span class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            {{ editMode ? 'Drag waveform to select speaker' : 'Waveform (click to scrub)' }}
          </span>
          <div class="flex items-center gap-1.5">
            <button
              type="button"
              :disabled="isDecoding || isDiarizing || isAnalyzing"
              class="rounded-lg border border-brand-green/40 bg-[#2f6b5e] px-2.5 py-1 text-[11px] font-bold text-slate-100 transition hover:bg-[#387c6d] disabled:opacity-40"
              @click="autoDetectSpeakers"
            >
              {{ isDiarizing ? 'Detecting Speakers...' : 'Auto-Split Speakers' }}
            </button>
            <button
              type="button"
              :disabled="isDecoding || isAnalyzing"
              :class="[
                'rounded-lg border px-2.5 py-1 text-[11px] font-semibold transition',
                editMode
                  ? 'border-white/40 bg-white/15 text-slate-100'
                  : 'border-white/15 bg-white/5 text-slate-300 hover:border-white/30 hover:text-slate-100',
              ]"
              @click="editMode = !editMode"
            >
              {{ editMode ? 'Manual Split: ON' : 'Manual Split' }}
            </button>
          </div>
        </div>

        <canvas
          ref="canvasRef"
          width="480"
          height="78"
          class="h-[78px] w-full cursor-crosshair rounded-xl border border-white/15"
          @pointerdown="onWaveDown"
          @pointermove="onWaveMove"
          @pointerup="onWaveUp"
          @pointerleave="onWaveUp"
        />
      </div>

      <!-- Manual & Auto Speaker Clip Editor -->
      <div v-if="editMode" class="flex flex-col gap-2.5 rounded-xl border border-white/15 bg-back-prime/65 p-3">
        <p class="text-[11px] text-slate-400">
          Each unique speaker label is saved as its own separate session in Detection History.
        </p>

        <div class="grid grid-cols-2 gap-2 sm:grid-cols-3">
          <div>
            <label class="text-[10px] font-semibold uppercase text-slate-400">Start (s)</label>
            <input
              v-model.number="draftStart"
              type="number"
              min="0"
              :max="duration"
              step="0.5"
              class="mt-1 h-8 w-full rounded-lg border border-white/15 bg-white/5 px-2.5 text-xs tabular-nums text-slate-100 focus:border-white/40 focus:outline-none"
            />
          </div>
          <div>
            <label class="text-[10px] font-semibold uppercase text-slate-400">End (s)</label>
            <input
              v-model.number="draftEnd"
              type="number"
              min="0"
              :max="duration"
              step="0.5"
              class="mt-1 h-8 w-full rounded-lg border border-white/15 bg-white/5 px-2.5 text-xs tabular-nums text-slate-100 focus:border-white/40 focus:outline-none"
            />
          </div>
          <div class="col-span-2 sm:col-span-1">
            <label class="text-[10px] font-semibold uppercase text-slate-400">Speaker Label</label>
            <input
              v-model="draftLabel"
              type="text"
              maxlength="60"
              placeholder="e.g. Candidate"
              class="mt-1 h-8 w-full rounded-lg border border-white/15 bg-white/5 px-2.5 text-xs text-slate-100 placeholder:text-slate-500 focus:border-white/40 focus:outline-none"
            />
          </div>
        </div>

        <div class="flex items-center justify-between gap-2">
          <button
            type="button"
            :disabled="!hasValidDraft"
            class="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-200 transition hover:bg-white/15 disabled:opacity-35"
            @click="playClipRange(draftStart, draftEnd)"
          >
            Preview Selection
          </button>
          <button
            type="button"
            :disabled="!hasValidDraft"
            class="rounded-lg bg-white/15 px-3 py-1 text-[11px] font-bold text-slate-100 transition hover:bg-white/25 disabled:opacity-35"
            @click="addClip"
          >
            + Add Speaker Clip
          </button>
        </div>

        <div v-if="clips.length" class="flex max-h-[130px] flex-col gap-1.5 overflow-y-auto pt-1">
          <div
            v-for="c in clips"
            :key="c.id"
            class="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-xs"
          >
            <div class="flex min-w-0 flex-1 items-center gap-2">
              <span class="size-2.5 shrink-0 rounded-full" :style="{ backgroundColor: c.color.replace('0.30', '0.9') }" />
              <input
                v-model="c.label"
                type="text"
                maxlength="60"
                class="min-w-0 flex-1 bg-transparent text-xs font-semibold text-slate-100 focus:outline-none"
              />
              <span class="shrink-0 text-[11px] tabular-nums text-slate-400">
                {{ formatSec(c.start_s) }} - {{ formatSec(c.end_s) }}
              </span>
            </div>
            <div class="flex items-center gap-1.5">
              <button
                type="button"
                class="rounded px-1.5 py-0.5 text-[10px] font-semibold text-slate-300 hover:bg-white/10 hover:text-white"
                @click="playClipRange(c.start_s, c.end_s)"
              >
                Play
              </button>
              <button
                type="button"
                class="rounded px-1.5 py-0.5 text-xs text-slate-400 hover:bg-red-500/20 hover:text-red-300"
                @click="removeClip(c.id)"
              >
                &times;
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Session Title + Chunk Size -->
      <div class="flex flex-col gap-3">
        <div>
          <label for="upload-session-title" class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Session Title
          </label>
          <input
            id="upload-session-title"
            v-model="sessionTitle"
            type="text"
            maxlength="120"
            placeholder="e.g. Interview Recording"
            class="mt-1 h-9 w-full rounded-xl border border-white/15 bg-back-prime px-3 text-xs text-slate-100 placeholder:text-slate-500 focus:border-white/40 focus:outline-none"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label for="upload-chunk-size" class="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Chunk size: <span class="text-sm normal-case tracking-normal text-slate-100">{{ chunkSize }}s</span>
          </label>
          <input
            id="upload-chunk-size"
            v-model.number="chunkSize"
            type="range"
            min="1"
            max="15"
            step="1"
            :disabled="isAnalyzing"
            class="h-1.5 w-full cursor-pointer accent-brand-green"
          />
        </div>
      </div>

      <!-- Live Chunk Streaming Progress -->
      <div v-if="isAnalyzing || progressText" class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-[11px] text-slate-300">
          <span class="truncate">{{ progressText }}</span>
          <span class="tabular-nums font-semibold text-slate-100">{{ progressPct }}%</span>
        </div>
        <div class="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
          <div
            class="h-full rounded-full bg-brand-green transition-all duration-300"
            :style="{ width: `${progressPct}%` }"
          />
        </div>
      </div>

      <p v-if="localError" class="rounded-xl border border-red-400/30 bg-red-400/10 px-3 py-2 text-xs text-red-300">
        {{ localError }}
      </p>

      <!-- Analyze / Cancel CTA -->
      <div class="flex items-center gap-2">
        <button
          type="button"
          :disabled="isDecoding || isAnalyzing || isDiarizing || disabled"
          class="h-10 flex-1 rounded-xl bg-gradient-to-r from-[#b7d894] via-[#c3e2a2] to-[#a7cb82] px-4 text-xs font-bold text-back-prime shadow-sm transition hover:brightness-105 disabled:opacity-45"
          @click="analyzeRecording"
        >
          {{
            isAnalyzing
              ? 'Streaming Chunks...'
              : editMode && clips.length
                ? `Analyze ${new Set(clips.map((c) => c.label)).size} Speaker Session${new Set(clips.map((c) => c.label)).size === 1 ? '' : 's'}`
                : 'Analyze Full Recording'
          }}
        </button>
        <button
          v-if="isAnalyzing"
          type="button"
          class="h-10 rounded-xl border border-red-400/40 bg-red-500/20 px-3.5 text-xs font-bold text-red-200 transition hover:bg-red-500/35"
          @click="stopAnalysis"
        >
          Stop
        </button>
      </div>
    </template>
  </div>
</template>
