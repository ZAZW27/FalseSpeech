import { onBeforeUnmount, onMounted, ref, watch, computed } from 'vue'
import { WS_BASE, authFetch, clearToken, getToken } from '@/assets/js/api'

// Ported from the legacy HTML/JS detector.
const SILENCE_THRESHOLD_BYTES = 10000 // blobs smaller than this are flagged as silence
const VERDICT_THRESHOLD = 0.7
const CHUNK_GRACE_MS = 500 // extra wait between chunks, same as legacy
const SILENT_VOLUME = 5 // visualizer volume (0-100) under which the bar is gray
const MAX_LOGS = 200
const MAX_HISTORY = 100
const EXPIRED_REDIRECT_MS = 1500
const FUP_MARKER = 'fair usage policy exceeded'

const PREF_KEYS = {
  chunkSize: 'fs_pref_chunk_size',
  mode: 'fs_pref_capture_mode',
  device: 'fs_pref_audio_device',
  verifiedDevices: 'fs_pref_verified_devices',
}

const RECORDER_MIME_CANDIDATES = [
  'audio/webm;codecs=opus',
  'audio/webm',
  'audio/ogg;codecs=opus',
  'audio/ogg',
  'audio/mp4',
]

const pickSupportedMime = () => {
  if (typeof MediaRecorder === 'undefined' || !MediaRecorder.isTypeSupported) return ''
  return RECORDER_MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m)) ?? ''
}

const readPref = (key, fallback) => {
  try {
    const val = localStorage.getItem(key)
    return val !== null ? val : fallback
  } catch {
    return fallback
  }
}

const loadVerifiedDevices = () => {
  try {
    const raw = localStorage.getItem(PREF_KEYS.verifiedDevices)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const writePref = (key, value) => {
  try {
    localStorage.setItem(key, String(value))
  } catch {
    // Ignore private-mode storage quota errors
  }
}

const loadSavedChunkSize = () => {
  const n = Number(readPref(PREF_KEYS.chunkSize, '10'))
  return Number.isFinite(n) && n >= 1 && n <= 15 ? Math.round(n) : 10
}

const loadSavedMode = () => {
  const m = readPref(PREF_KEYS.mode, 'monitor')
  return m === 'tab' || m === 'monitor' ? m : 'monitor'
}

const NO_PROCESSING = { echoCancellation: false, noiseSuppression: false, autoGainControl: false }

// real/fake probabilities -> label and tone. Same order as the legacy code.
export const classifyChunk = ({ silent, real, fake }) => {
  if (silent) return { label: 'SILENT', tone: 'uncertain' }
  if (real >= VERDICT_THRESHOLD) return { label: 'REAL', tone: 'real' }
  if (fake >= VERDICT_THRESHOLD) return { label: 'FAKE', tone: 'fake' }
  return { label: 'UNCERTAIN', tone: 'uncertain' }
}

// options.onQuota(used, limit): called when the server reports quota.
// options.onSessionExpired(): called after the server closes with code 1008.
// options.onFairUsage(message): called when the server reports the Fair Usage Policy was exceeded.
export function useAudioCapture(options = {}) {
  // Public state
  const isListening = ref(false)
  const currentResult = ref(null) // { label, tone, fake, real, silent, size, segmentIndex }
  const liveLogs = ref([]) // { id, time, text, tone: 'fake' | 'real' | 'warn' | 'muted' }
  const history = ref([]) // live inference history, newest first
  const devices = ref([]) // { deviceId, label }
  const verifiedDevices = ref(loadVerifiedDevices()) // deviceIds confirmed to carry audio signal
  const selectedDevice = ref(readPref(PREF_KEYS.device, ''))
  const mode = ref(loadSavedMode()) // 'monitor' (Mode A) | 'tab' (Mode B)
  const chunkSize = ref(loadSavedChunkSize()) // seconds, 1 to 15

  const markVerifiedDevices = (ids) => {
    const unique = [...new Set((ids || []).filter(Boolean))]
    verifiedDevices.value = unique
    try {
      localStorage.setItem(PREF_KEYS.verifiedDevices, JSON.stringify(unique))
    } catch {}
  }
  const volume = ref(0) // 0 to 100
  const statusText = ref('')
  const statusWarn = ref(false)
  const errorMessage = ref('')
  const fairUsageExceeded = ref(false)

  const hasAudio = computed(() => volume.value >= SILENT_VOLUME)
  const verdict = computed(() => currentResult.value?.label ?? null)

  // Internal state
  let stream = null // audio only stream used for recording
  let displayStream = null // full getDisplayMedia stream, kept so its video track can be stopped
  let chunkTimer = null
  let sessionId = 0 // bumped on start and stop, so late results from old sessions are ignored
  let backendSessionId = null // server DetectionSessionRow.id shared by all chunks in this listening run
  let isStarting = false
  let logId = 0
  let audioCtx = null
  let analyser = null
  let source = null
  let vizFrame = null

  const pushLog = (text, tone = 'muted') => {
    liveLogs.value.push({ id: ++logId, time: new Date().toLocaleTimeString(), text, tone })
    if (liveLogs.value.length > MAX_LOGS) liveLogs.value.splice(0, liveLogs.value.length - MAX_LOGS)
  }

  // Persist user preferences so scaler, capture mode, and input device survive reloads.
  watch(chunkSize, (value) => {
    writePref(PREF_KEYS.chunkSize, value)
    pushLog(`chunk size -> ${value}s`)
  })
  watch(mode, (value) => {
    writePref(PREF_KEYS.mode, value)
  })
  watch(selectedDevice, (value) => {
    if (value) writePref(PREF_KEYS.device, value)
  })

  // ---------- Devices (Mode A) ----------
  const refreshDevices = async () => {
    if (!navigator.mediaDevices?.enumerateDevices) return

    // Labels are empty until the user grants microphone permission once.
    try {
      const temp = await navigator.mediaDevices.getUserMedia({ audio: true })
      temp.getTracks().forEach((track) => track.stop())
    } catch (error) {
      pushLog(`mic permission denied: ${error.message}`, 'warn')
    }

    const all = await navigator.mediaDevices.enumerateDevices()
    devices.value = all
      .filter((device) => device.kind === 'audioinput')
      .map((device) => ({
        deviceId: device.deviceId,
        label: device.label || `Input ${device.deviceId.slice(0, 8)}`,
      }))
    pushLog(`found ${devices.value.length} audio inputs`)

    // Prefer user's previously cached audio device if still connected
    const savedId = readPref(PREF_KEYS.device, '')
    const savedMatch = savedId && devices.value.find((device) => device.deviceId === savedId)
    if (savedMatch) {
      selectedDevice.value = savedMatch.deviceId
      pushLog(`restored preferred input: ${savedMatch.label}`)
      return
    }

    const monitor = devices.value.find((device) => device.label.toLowerCase().includes('monitor'))
    if (monitor) {
      selectedDevice.value = monitor.deviceId
      pushLog(`auto-selected: ${monitor.label}`)
    } else if (!devices.value.some((device) => device.deviceId === selectedDevice.value)) {
      selectedDevice.value = devices.value[0]?.deviceId ?? ''
    }
  }

  // ---------- Capture modes ----------
  const openMonitor = async () => {
    if (!selectedDevice.value) throw new Error('Pick a device first.')
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: selectedDevice.value }, ...NO_PROCESSING },
      })
    } catch {
      // Fallback for browsers (e.g. Brave/Safari/Firefox) that reject strict exact/NO_PROCESSING constraints
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: selectedDevice.value },
      })
    }
    const label = devices.value.find((device) => device.deviceId === selectedDevice.value)?.label
    pushLog(`mode A - capturing from: ${label ?? selectedDevice.value}`)
  }

  const openTab = async () => {
    if (!navigator.mediaDevices?.getDisplayMedia) {
      throw new Error('This browser does not support screen/system audio sharing. Use Mode A instead.')
    }
    let display
    try {
      // Google Meet–style display capture: enables "Also share system audio" on Chrome, Brave & Edge
      display = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: { ...NO_PROCESSING, suppressLocalAudioPlayback: false },
        systemAudio: 'include',
        selfBrowserSurface: 'include',
        surfaceSwitching: 'include',
      })
    } catch (err) {
      // Fallback for Firefox/Safari if Chromium-specific keys throw TypeError/OverconstrainedError
      if (err?.name === 'NotAllowedError' || err?.name === 'AbortError') throw err
      display = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
    }
    const audioTracks = display.getAudioTracks()

    if (audioTracks.length === 0) {
      pushLog('mode B - NO AUDIO TRACK. Check "Share tab audio" or "Share system audio".', 'warn')
      display.getTracks().forEach((track) => track.stop())
      throw new Error('No audio track shared. Enable "Share tab audio" or "Share system audio" in the picker.')
    }

    displayStream = display
    const videoTrack = display.getVideoTracks()[0]
    if (videoTrack) {
      videoTrack.onended = () => {
        pushLog('user stopped sharing')
        stopCapture()
      }
    }
    stream = new MediaStream(audioTracks)
    pushLog('mode B - tab/system audio captured')
  }

  // ---------- Visualizer ----------
  const startVisualizer = (mediaStream) => {
    const Context = window.AudioContext || window.webkitAudioContext
    if (!Context) return

    audioCtx = new Context()
    analyser = audioCtx.createAnalyser()
    analyser.fftSize = 256
    source = audioCtx.createMediaStreamSource(mediaStream)
    source.connect(analyser)

    const data = new Uint8Array(analyser.frequencyBinCount)
    const draw = () => {
      analyser.getByteFrequencyData(data)
      let sum = 0
      for (let i = 0; i < data.length; i++) sum += data[i]
      const average = sum / data.length
      volume.value = Math.min(100, (average / 128) * 100 * 2)
      vizFrame = requestAnimationFrame(draw)
    }
    draw()
  }

  const stopVisualizer = () => {
    if (vizFrame) cancelAnimationFrame(vizFrame)
    vizFrame = null
    source?.disconnect()
    source = null
    analyser = null
    if (audioCtx) audioCtx.close().catch(() => {})
    audioCtx = null
    volume.value = 0
  }

  // ---------- Chunks ----------
  const recordChunk = () => {
    if (!isListening.value || !stream) return

    const currentSession = sessionId
    const chunks = []
    const mime = pickSupportedMime()

    const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined)
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunks.push(event.data)
    }
    recorder.onstop = () => {
      // A stopped session never sends its last partial chunk.
      if (currentSession !== sessionId) return
      if (chunks.length === 0) {
        pushLog('empty chunk', 'warn')
        return
      }
      sendChunk(new Blob(chunks, { type: mime || recorder.mimeType || 'audio/webm' }), currentSession)
    }

    recorder.start()
    setTimeout(() => {
      if (recorder.state === 'recording') recorder.stop()
    }, chunkSize.value * 1000)
  }

  const scheduleNextChunk = () => {
    if (!isListening.value) return
    chunkTimer = setTimeout(() => {
      recordChunk()
      scheduleNextChunk()
    }, chunkSize.value * 1000 + CHUNK_GRACE_MS)
  }

  // One WebSocket per chunk: connect, send the blob, read one result, close.
  // All chunks in the same listening run pass the same backendSessionId so they group under one session.
  const sendChunk = (blob, currentSession) => {
    const silent = blob.size < SILENCE_THRESHOLD_BYTES
    statusText.value = `chunk: ${blob.size} bytes${silent ? ' -- LIKELY SILENCE' : ''}`
    statusWarn.value = silent

    const qs = new URLSearchParams({ token: getToken() ?? '', source: 'web' })
    if (backendSessionId) qs.set('session_id', String(backendSessionId))
    const ws = new WebSocket(`${WS_BASE}/ws/audio?${qs.toString()}`)
    ws.binaryType = 'arraybuffer'

    ws.onopen = async () => {
      pushLog(`sending ${blob.size} bytes`)
      ws.send(await blob.arrayBuffer())
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (currentSession !== sessionId) return // session was stopped meanwhile
        if (data.session_id && !backendSessionId) backendSessionId = data.session_id

        if (data.error) {
          pushLog(`error: ${data.error}`, 'warn')

          // Fair Usage Policy: tell the user, then stop listening.
          if (String(data.error).toLowerCase().includes(FUP_MARKER)) {
            fairUsageExceeded.value = true
            errorMessage.value = `${data.error}. Listening was stopped.`
            options.onFairUsage?.(data.error)
            stopCapture()
          }
          return
        }

        const fake = Number(data.fek_prob) || 0
        const real = Number(data.ril_prob) || 0
        const { label, tone } = classifyChunk({ silent, real, fake })

        currentResult.value = { label, tone, fake, real, silent, size: blob.size, segmentIndex: data.segment_index }
        history.value.unshift({
          id: `${data.session_id ?? 's'}-${data.segment_index ?? Date.now()}-${blob.size}`,
          time: new Date().toLocaleTimeString(),
          chunk: data.segment_index ?? '?',
          size: blob.size,
          label,
          tone,
          fake,
        })
        if (history.value.length > MAX_HISTORY) history.value.length = MAX_HISTORY

        pushLog(
          `result: ${label} (fake=${fake.toFixed(3)}, session=${data.session_id}, quota=${data.quota_used}/${data.quota_limit})`,
          tone === 'uncertain' ? 'warn' : tone,
        )

        if (data.quota_used != null) options.onQuota?.(data.quota_used, data.quota_limit)
      } catch (error) {
        pushLog(`parse error: ${error.message}`, 'warn')
      } finally {
        ws.close()
      }
    }

    ws.onerror = () => pushLog('ws network error', 'warn')
    ws.onclose = (event) => {
      if (event.code === 1008) {
        pushLog('Session expired. Redirecting to login...', 'warn')
        clearToken()
        stopCapture()
        setTimeout(() => options.onSessionExpired?.(), EXPIRED_REDIRECT_MS)
      } else if (event.code !== 1000 && event.code !== 1005) {
        pushLog(`ws closed unexpectedly: Code ${event.code} - ${event.reason}`, 'warn')
      }
    }
  }

  // ---------- Start and stop ----------
  const releaseStreams = () => {
    stream?.getTracks().forEach((track) => track.stop())
    displayStream?.getTracks().forEach((track) => track.stop())
    stream = null
    displayStream = null
  }

  const readableError = (error) => {
    if (error?.name === 'NotAllowedError') return 'Permission was denied or the share was cancelled.'
    if (error?.name === 'NotFoundError') return 'The selected audio device was not found.'
    return error?.message || 'Could not start capture.'
  }

  const startCapture = async () => {
    if (isListening.value || isStarting) return
    if (!getToken()) {
      errorMessage.value = 'You are not logged in.'
      return
    }
    if (!navigator.mediaDevices) {
      errorMessage.value = 'This browser does not support audio capture.'
      return
    }

    isStarting = true
    errorMessage.value = ''
    fairUsageExceeded.value = false

    try {
      if (mode.value === 'monitor') await openMonitor()
      else await openTab()
    } catch (error) {
      pushLog(`start failed: ${error.message}`, 'warn')
      errorMessage.value = readableError(error)
      releaseStreams()
      isStarting = false
      return
    }

    isStarting = false
    sessionId += 1
    backendSessionId = null
    isListening.value = true
    currentResult.value = null
    history.value = [] // new session starts with an empty history
    statusText.value = ''
    statusWarn.value = false

    // Create one server-side session upfront so every chunk in this listening run shares one session_id
    try {
      const res = await authFetch('/api/history/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'web' }),
      })
      if (res.ok) {
        const created = await res.json()
        if (created?.session_id) {
          backendSessionId = created.session_id
          pushLog(`started listening session #${backendSessionId}`)
        }
      }
    } catch {
      // Fallback: first WS chunk will auto-create and return session_id
    }

    startVisualizer(stream)
    recordChunk()
    scheduleNextChunk()
  }

  function stopCapture() {
    if (!isListening.value) return
    isListening.value = false
    sessionId += 1
    backendSessionId = null
    clearTimeout(chunkTimer)
    chunkTimer = null
    releaseStreams()
    stopVisualizer()
    statusText.value = ''
    statusWarn.value = false
    pushLog('stopped')
  }

  onMounted(() => {
    refreshDevices()
    navigator.mediaDevices?.addEventListener?.('devicechange', refreshDevices)
  })

  onBeforeUnmount(() => {
    navigator.mediaDevices?.removeEventListener?.('devicechange', refreshDevices)
    stopCapture()
  })

  return {
    isListening,
    currentResult,
    liveLogs,
    history,
    devices,
    verifiedDevices,
    markVerifiedDevices,
    selectedDevice,
    mode,
    chunkSize,
    volume,
    hasAudio,
    verdict,
    statusText,
    statusWarn,
    errorMessage,
    fairUsageExceeded,
    refreshDevices,
    startCapture,
    stopCapture,
  }
}
