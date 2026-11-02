import { computed, onBeforeUnmount, ref } from 'vue'
import { WS_BASE, getToken } from '@/assets/js/api'

// Each recorded segment is a complete, self-contained webm/opus file, so the backend
// can decode every blob on its own. Change this if the backend expects a continuous stream.
const SEGMENT_MS = 3000
const MAX_LOGS = 200
// If neither probability reaches this value, the verdict is UNCERTAIN.
const UNCERTAIN_BELOW = 0.6
const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm']

// WS result -> 'REAL' | 'FAKE' | 'UNCERTAIN' | null
export const getVerdict = (result) => {
  if (!result) return null
  const fake = Number(result.fek_prob) || 0
  const real = Number(result.ril_prob) || 0
  if (Math.max(fake, real) < UNCERTAIN_BELOW) return 'UNCERTAIN'
  return result.is_fek ? 'FAKE' : 'REAL'
}

const percent = (value) => `${Math.round((Number(value) || 0) * 100)}%`

export function useAudioCapture() {
  // 'idle' | 'connecting' | 'listening'
  const status = ref('idle')
  const currentResult = ref(null)
  const liveLogs = ref([])
  const errorMessage = ref('')

  const isListening = computed(() => status.value !== 'idle')
  const verdict = computed(() => getVerdict(currentResult.value))

  let socket = null
  let stream = null
  let recorder = null
  let segmentTimer = null
  let onQuota = null
  let logId = 0
  let wanted = false

  const pushLog = (text, tone = 'muted') => {
    liveLogs.value.push({
      id: ++logId,
      time: new Date().toLocaleTimeString([], { hour12: false }),
      text,
      tone,
    })
    if (liveLogs.value.length > MAX_LOGS) {
      liveLogs.value.splice(0, liveLogs.value.length - MAX_LOGS)
    }
  }

  // Safe to call more than once.
  const teardown = () => {
    wanted = false
    clearTimeout(segmentTimer)
    segmentTimer = null

    if (recorder) {
      recorder.onstop = null
      recorder.ondataavailable = null
      if (recorder.state !== 'inactive') recorder.stop()
      recorder = null
    }

    if (stream) {
      stream.getTracks().forEach((track) => track.stop())
      stream = null
    }

    if (socket) {
      socket.onopen = null
      socket.onmessage = null
      socket.onerror = null
      socket.onclose = null
      if (socket.readyState < WebSocket.CLOSING) socket.close()
      socket = null
    }

    status.value = 'idle'
  }

  const recordSegment = () => {
    if (!wanted || !stream) return

    const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type))
    recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined)

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0 && socket?.readyState === WebSocket.OPEN) {
        socket.send(event.data)
      }
    }
    // When a segment ends, start the next one right away.
    recorder.onstop = () => {
      if (wanted) recordSegment()
    }

    recorder.start()
    segmentTimer = setTimeout(() => {
      if (recorder?.state === 'recording') recorder.stop()
    }, SEGMENT_MS)
  }

  const handleMessage = (event) => {
    let data
    try {
      data = JSON.parse(event.data)
    } catch {
      pushLog('Received an unreadable message from the server.', 'muted')
      return
    }

    currentResult.value = data
    const label = getVerdict(data)
    pushLog(
      `seg ${data.segment_index ?? '-'}  ${label}  fake ${percent(data.fek_prob)}  real ${percent(data.ril_prob)}`,
      label === 'FAKE' ? 'fake' : label === 'REAL' ? 'real' : 'muted',
    )

    if (data.quota_used != null && onQuota) onQuota(data.quota_used, data.quota_limit)
  }

  // options.onQuota(used, limit) is called whenever the server reports quota.
  const start = async (options = {}) => {
    if (status.value !== 'idle') return

    const token = getToken()
    if (!token) {
      errorMessage.value = 'You are not logged in.'
      return
    }
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      errorMessage.value = 'This browser does not support audio capture.'
      return
    }

    errorMessage.value = ''
    currentResult.value = null
    liveLogs.value = []
    onQuota = options.onQuota ?? null
    wanted = true
    status.value = 'connecting'

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      teardown()
      errorMessage.value = 'Microphone access was denied. Allow it in your browser settings and try again.'
      return
    }

    // The user may have pressed stop while the permission prompt was open.
    if (!wanted) {
      teardown()
      return
    }

    pushLog('Connecting...', 'muted')
    socket = new WebSocket(`${WS_BASE}/ws/audio?token=${encodeURIComponent(token)}`)

    socket.onopen = () => {
      status.value = 'listening'
      pushLog('Connected. Listening...', 'muted')
      recordSegment()
    }
    socket.onmessage = handleMessage
    socket.onerror = () => {
      errorMessage.value = 'Connection error. Please try again.'
    }
    socket.onclose = () => {
      if (!wanted) return
      if (!errorMessage.value) errorMessage.value = 'The connection was closed by the server.'
      pushLog('Connection closed.', 'muted')
      teardown()
    }
  }

  const stop = () => {
    if (status.value === 'idle') return
    pushLog('Stopped.', 'muted')
    teardown()
  }

  onBeforeUnmount(teardown)

  return { status, isListening, currentResult, verdict, liveLogs, errorMessage, start, stop }
}
