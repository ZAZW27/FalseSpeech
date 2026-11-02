// Shared helpers for the authenticated part of the app.
export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:7860'
export const WS_BASE = API_BASE.replace(/^http/, 'ws')
export const TOKEN_KEY = 'access_token'

export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export const clearToken = () => {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can be unavailable (private mode). Nothing to clear then.
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
