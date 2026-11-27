import { computed, ref } from 'vue'

const STORAGE_KEY = 'fs_pref_spike_alerts'
const CONSECUTIVE_REQUIRED = 2
const COOLDOWN_MS = 20000

const readSavedPref = () => {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}

const playSubtleAlertChime = () => {
  try {
    const Context = window.AudioContext || window.webkitAudioContext
    if (!Context) return
    const ctx = new Context()
    const now = ctx.currentTime
    const freqs = [587.33, 440.0]
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, now + i * 0.16)
      gain.gain.setValueAtTime(0.001, now + i * 0.16)
      gain.gain.exponentialRampToValueAtTime(0.08, now + i * 0.16 + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.16 + 0.14)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(now + i * 0.16)
      osc.stop(now + i * 0.16 + 0.15)
    })
    setTimeout(() => ctx.close().catch(() => {}), 500)
  } catch {
    // Ignore autoplay restrictions
  }
}

export function useSpikeAlert() {
  const isSupported = typeof window !== 'undefined' && 'Notification' in window
  const permission = ref(isSupported ? Notification.permission : 'unsupported')
  const alertsEnabled = ref(readSavedPref() && permission.value === 'granted')
  const alertNotice = ref('')

  let consecutiveFake = 0
  let lastAlertAt = 0

  const isDenied = computed(() => permission.value === 'denied')

  const savePref = (val) => {
    try {
      localStorage.setItem(STORAGE_KEY, String(val))
    } catch {}
  }

  const toggleAlerts = async () => {
    alertNotice.value = ''
    if (!isSupported) {
      alertNotice.value = 'Desktop notifications are not supported in this browser.'
      return
    }

    if (alertsEnabled.value) {
      alertsEnabled.value = false
      savePref(false)
      consecutiveFake = 0
      return
    }

    if (Notification.permission === 'denied') {
      permission.value = 'denied'
      alertNotice.value = 'Notifications are blocked in browser site settings.'
      return
    }

    let result = Notification.permission
    if (result !== 'granted') {
      try {
        result = await Notification.requestPermission()
      } catch {
        result = 'denied'
      }
    }

    permission.value = result
    if (result === 'granted') {
      alertsEnabled.value = true
      savePref(true)
    } else {
      alertsEnabled.value = false
      savePref(false)
      alertNotice.value = 'Notification permission was not granted.'
    }
  }

  const resetStreak = () => {
    consecutiveFake = 0
  }

  const recordVerdict = (result) => {
    if (!result) return
    if (result.label === 'FAKE' && !result.silent) {
      consecutiveFake += 1
    } else {
      consecutiveFake = 0
      return
    }

    if (!alertsEnabled.value || !isSupported || Notification.permission !== 'granted') return
    if (consecutiveFake < CONSECUTIVE_REQUIRED) return

    const now = Date.now()
    if (now - lastAlertAt < COOLDOWN_MS) return
    lastAlertAt = now

    const pct = Math.round((Number(result.fake) || 0) * 100)
    try {
      const notif = new Notification('False Speech: AI Voice Detected', {
        body: `${consecutiveFake} consecutive synthetic voice spikes detected (${pct}% AI risk). Click to inspect.`,
        icon: '/favicon.svg',
        tag: 'falsespeech-ai-spike',
      })
      notif.onclick = () => {
        window.focus()
        notif.close()
      }
      if (document.hidden) playSubtleAlertChime()
    } catch {
      // Ignore notification delivery errors
    }
  }

  return {
    isSupported,
    permission,
    isDenied,
    alertsEnabled,
    alertNotice,
    toggleAlerts,
    recordVerdict,
    resetStreak,
  }
}
