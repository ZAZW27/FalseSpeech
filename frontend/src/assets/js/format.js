// 6120 -> "1h 42m", 18000 -> "5h", 2520 -> "42m", 45 -> "45s"
export const formatDuration = (totalSeconds) => {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0))
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)

  if (h > 0 && m > 0) return `${h}h ${m}m`
  if (h > 0) return `${h}h`
  if (m > 0) return `${m}m`
  return `${seconds}s`
}

// used / limit as a whole number between 0 and 100.
export const toPercent = (used, limit) => {
  if (!limit || limit <= 0) return 0
  return Math.min(100, Math.max(0, Math.round((used / limit) * 100)))
}

export const capitalize = (text = '') => text.charAt(0).toUpperCase() + text.slice(1)

export const getInitials = (name = '') =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')

// 204 -> "03:24", 4262 -> "1:11:02"
export const formatClock = (totalSeconds) => {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0))
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  const pad = (value) => String(value).padStart(2, '0')
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`
}

// Local calendar day as "YYYY-MM-DD".
export const dayKey = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

// ISO string -> "Today, 08:12", "Yesterday, 21:30" or "Oct 13, 19:22"
export const formatSessionTime = (iso, now = new Date()) => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '-'

  const time = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1)

  if (dayKey(date) === dayKey(now)) return `Today, ${time}`
  if (dayKey(date) === dayKey(yesterday)) return `Yesterday, ${time}`
  return `${date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}, ${time}`
}

// ISO string -> "Oct 20, 2026 - 10:00 AM"
export const formatDateTime = (iso) => {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '-'
  const day = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  const time = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  return `${day} - ${time}`
}

// 42 -> "42s", 90 -> "1m 30s", 120 -> "2m", 3700 -> "1h 1m"
export const formatSessionDuration = (totalSeconds) => {
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0))
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  if (h > 0) return m > 0 ? `${h}h ${m}m` : `${h}h`
  if (m > 0) return s > 0 ? `${m}m ${s}s` : `${m}m`
  return `${s}s`
}

// 0.452 -> 45.2
export const ratioToPercent = (ratio) =>
  Math.round(Math.min(1, Math.max(0, Number(ratio) || 0)) * 1000) / 10
