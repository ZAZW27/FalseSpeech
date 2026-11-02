import { onBeforeUnmount, onMounted, ref, watch, computed } from 'vue'
import { WS_BASE, clearToken, getToken } from '@/assets/js/api'

// Ported from the legacy HTML/JS detector.
const SILENCE_THRESHOLD_BYTES = 10000 // blobs smaller than this are flagged as silence
const VERDICT_THRESHOLD = 0.7
const CHUNK_GRACE_MS = 500 // extra wait between chunks, same as legacy
const SILENT_VOLUME = 5 // visualizer volume (0-100) under which the bar is gray
const MAX_LOGS = 200
const MAX_HISTORY = 100
const EXPIRED_REDIRECT_MS = 1500

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
export function useAudioCapture(options = {}) {
  // Public state
  const isListening = ref(false)
  const currentResult = ref(null) // { label, tone, fake, real, silent, size, segmentIndex }
  const liveLogs = ref([]) // { id, time, text, tone: 'fake' | 'real' | 'warn' | 'muted' }
  const history = ref([]) // live inference history, newest first
  const devices = ref([]) // { deviceId, label }
  const selectedDevice = ref('')
  const mode = ref('monitor') // 'monitor' (Mode A) | 'tab' (Mode B)
  const chunkSize = ref(10) // seconds, 1 to 15
  const volume = ref(0) // 0 to 100
  const statusText = ref('')
  const statusWarn = ref(false)
  const errorMessage = ref('')

  const hasAudio = computed(() => volume.value >= SILENT_VOLUME)
  const verdict = computed(() => currentResult.value?.label ?? null)

  // Internal state
  let stream = null // audio only stream used for recording
  let displayStream = null // full getDisplayMedia stream, kept so its video track can be stopped
  let chunkTimer = null
  let sessionId = 0 // bumped on start and stop, so late results from old sessions are ignored
  let isStarting = false
  let logId = 0
  let audioCtx = null
  let analyser = null
  let source = null
  let vizFrame = null

  // One WebSocket per listening session. It opens on Start and closes on Stop.
  let socket = null
  // Metadata of chunks already sent, in order. The server answers every chunk
  // exactly once and in order, so each reply takes the oldest entry.
  let pendingChunks = []

  const pushLog = (text, tone = 'muted') => {
    liveLogs.value.push({ id: ++logId, time: new Date().toLocaleTimeString(), text, tone })
    if (liveLogs.value.length > MAX_LOGS) liveLogs.value.splice(0, liveLogs.value.length - MAX_LOGS)
  }

  // The slider can change at any time. The next chunk uses the new value.
  watch(chunkSize, (value) => pushLog(`chunk size -> ${value}s`))

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
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { deviceId: { exact: selectedDevice.value }, ...NO_PROCESSING },
    })
    const label = devices.value.find((device) => device.deviceId === selectedDevice.value)?.label
    pushLog(`mode A - capturing from: ${label ?? selectedDevice.value}`)
  }

  const openTab = async () => {
    const display = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: NO_PROCESSING })
    const audioTracks = display.getAudioTracks()

    if (audioTracks.length === 0) {
      pushLog('mode B - NO AUDIO TRACK. Did you check "Share tab audio"?', 'warn')
      display.getTracks().forEach((track) => track.stop())
      throw new Error('No audio track. Enable "Share tab audio" when choosing the tab.')
    }

    displayStream = display
    display.getVideoTracks()[0].onended = () => {
      pushLog('user stopped sharing')
      stopCapture()
    }
    stream = new MediaStream(audioTracks)
    pushLog('mode B - tab audio captured')
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

  // ---------- WebSocket (one connection per session) ----------
  const handleMessage = (event, currentSession) => {
    // Always take the metadata entry, even for stale sessions, to keep the queue aligned.
    const meta = pendingChunks.shift() ?? { size: 0, silent: false }

    try {
      const data = JSON.parse(event.data)
      if (currentSession !== sessionId) return // session was stopped meanwhile

      if (data.error) {
        pushLog(`error: ${data.error}`, 'warn')
        if (data.error === 'quota exceeded') {
          if (data.quota_used != null) options.onQuota?.(data.quota_used, data.quota_limit)
          errorMessage.value = 'Daily quota reached. Listening stopped.'
          stopCapture()
        }
        return
      }

      const { silent, size } = meta
      const fake = Number(data.fek_prob) || 0
      const real = Number(data.ril_prob) || 0
      const { label, tone } = classifyChunk({ silent, real, fake })

      currentResult.value = { label, tone, fake, real, silent, size, segmentIndex: data.segment_index }
      history.value.unshift({
        id: `${data.session_id ?? 's'}-${data.segment_index ?? Date.now()}-${size}`,
        time: new Date().toLocaleTimeString(),
        chunk: data.segment_index ?? '?',
        size,
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
    }
  }

  // Resolves once the socket is open. Rejects if it cannot connect.
  const connectSocket = (currentSession) =>
    new Promise((resolve, reject) => {
      const ws = new WebSocket(`${WS_BASE}/ws/audio?token=${encodeURIComponent(getToken() ?? '')}`)
      ws.binaryType = 'arraybuffer'
      let opened = false

      ws.onopen = () => {
        opened = true
        socket = ws
        pushLog('ws connected (one connection for this session)')
        resolve()
      }

      ws.onmessage = (event) => handleMessage(event, currentSession)

      ws.onerror = () => {
        pushLog('ws network error', 'warn')
        if (!opened) reject(new Error('Could not connect to the server.'))
      }

      ws.onclose = (event) => {
        if (!opened) {
          reject(new Error(event.reason || `Connection closed (code ${event.code}).`))
          return
        }
        if (socket === ws) socket = null

        // Closed by our own stopCapture, or by a newer session: nothing to do.
        if (currentSession !== sessionId) return

        if (event.code === 1008 && event.reason === 'quota exceeded') {
          pushLog('quota exceeded', 'warn')
          errorMessage.value = 'Daily quota reached. Listening stopped.'
          stopCapture()
        } else if (event.code === 1008) {
          pushLog('Session expired. Redirecting to login...', 'warn')
          clearToken()
          stopCapture()
          setTimeout(() => options.onSessionExpired?.(), EXPIRED_REDIRECT_MS)
        } else {
          pushLog(`ws closed unexpectedly: Code ${event.code} - ${event.reason}`, 'warn')
          errorMessage.value = 'Connection to the server was lost.'
          stopCapture()
        }
      }
    })

  const closeSocket = () => {
    const ws = socket
    socket = null
    pendingChunks = []
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      ws.close(1000, 'client stopped')
    }
  }

  // Sends one chunk through the already open socket.
  const sendChunk = (blob) => {
    const silent = blob.size < SILENCE_THRESHOLD_BYTES
    statusText.value = `chunk: ${blob.size} bytes${silent ? ' -- LIKELY SILENCE' : ''}`
    statusWarn.value = silent

    if (!socket || socket.readyState !== WebSocket.OPEN) {
      pushLog('socket not open, chunk dropped', 'warn')
      return
    }

    pendingChunks.push({ size: blob.size, silent })
    pushLog(`sending ${blob.size} bytes`)
    socket.send(blob)
  }

  // ---------- Chunks ----------
  const recordChunk = () => {
    if (!isListening.value || !stream) return

    const currentSession = sessionId
    const chunks = []
    let mime = 'audio/webm'
    if (!MediaRecorder.isTypeSupported(mime)) mime = ''

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
      sendChunk(new Blob(chunks, { type: mime || 'audio/webm' }))
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

    sessionId += 1
    const currentSession = sessionId

    // Open the single WebSocket for this session before recording anything.
    try {
      await connectSocket(currentSession)
    } catch (error) {
      pushLog(`start failed: ${error.message}`, 'warn')
      errorMessage.value = error.message
      sessionId += 1
      closeSocket()
      releaseStreams()
      isStarting = false
      return
    }

    // The user could have cancelled (for example by stopping the tab share) while connecting.
    if (currentSession !== sessionId) {
      closeSocket()
      releaseStreams()
      isStarting = false
      return
    }

    isStarting = false
    isListening.value = true
    currentResult.value = null
    history.value = [] // new session starts with an empty history
    pendingChunks = []
    statusText.value = ''
    statusWarn.value = false

    startVisualizer(stream)
    recordChunk()
    scheduleNextChunk()
  }

  function stopCapture() {
    if (!isListening.value) return
    isListening.value = false
    sessionId += 1
    clearTimeout(chunkTimer)
    chunkTimer = null
    closeSocket() // the server closes the session row when it sees this disconnect
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
    selectedDevice,
    mode,
    chunkSize,
    volume,
    hasAudio,
    verdict,
    statusText,
    statusWarn,
    errorMessage,
    refreshDevices,
    startCapture,
    stopCapture,
  }
}
