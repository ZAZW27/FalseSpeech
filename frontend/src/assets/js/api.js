// Shared helpers for the authenticated part of the app.
export const API_BASE = (
  import.meta.env.VITE_API_URL || 'https://falsespeech.putrahomelab.com'
).replace(/\/+$/, '')
export const WS_BASE = API_BASE.replace(/^http/, 'ws')
export const TOKEN_KEY = 'access_token'

const isTokenExpired = (token) => {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return true
    const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))
    if (typeof payload.exp !== 'number') return false
    return Date.now() >= payload.exp * 1000
  } catch {
    return true
  }
}

export const clearToken = () => {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be unavailable (private mode). Nothing to clear then.
  }
}

export const getToken = () => {
  try {
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) return null
    // Auto-clear expired JWTs client-side so stale sessions redirect to /login immediately.
    if (isTokenExpired(token)) {
      clearToken()
      return null
    }
    return token
  } catch {
    return null
  }
}

// fetch() with the JWT attached. Callers handle 401 themselves.
export const authFetch = (path, options = {}) =>
  fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.headers ?? {}),
      Authorization: `Bearer ${getToken()}`,
    },
  })
