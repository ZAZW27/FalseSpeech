import { dayKey } from '@/assets/js/format'

// Verdict values from GET /api/history: 'fake' | 'real' | 'mixed'
export const VERDICT_META = {
  fake: { label: 'AI voice', tone: 'danger' },
  real: { label: 'Human voice', tone: 'success' },
  mixed: { label: 'Mixed', tone: 'lime' },
}

export const getVerdictMeta = (verdict) =>
  VERDICT_META[verdict] ?? { label: verdict ?? 'Unknown', tone: 'lime' }

// total, AI voices (fake) and human voices (real or mixed).
export const summarizeHistory = (history = []) => ({
  total: history.length,
  ai: history.filter((item) => item.verdict === 'fake').length,
  human: history.filter((item) => item.verdict === 'real' || item.verdict === 'mixed').length,
})

// 0-100. fake -> fake_ratio, real -> 1 - fake_ratio, mixed -> the larger share.
export const confidenceOf = (item) => {
  const fake = Number(item?.fake_ratio) || 0
  let ratio
  if (item?.verdict === 'fake') ratio = fake
  else if (item?.verdict === 'real') ratio = 1 - fake
  else ratio = Math.max(fake, 1 - fake)
  return Math.round(Math.min(1, Math.max(0, ratio)) * 100)
}

// Sessions per day for the last 7 days (oldest first, today last).
export const buildWeekly = (history = [], now = new Date()) => {
  const counts = new Map()
  history.forEach((item) => {
    const date = new Date(item.started_at)
    if (Number.isNaN(date.getTime())) return
    const key = dayKey(date)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })

  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(now.getFullYear(), now.getMonth(), now.getDate() - (6 - index))
    const isToday = index === 6
    return {
      key: dayKey(date),
      label: isToday ? 'Today' : date.toLocaleDateString('en-US', { weekday: 'short' }),
      count: counts.get(dayKey(date)) ?? 0,
      isToday,
    }
  })
}
