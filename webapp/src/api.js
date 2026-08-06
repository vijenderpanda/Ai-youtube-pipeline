import { API_BASE, ANON_KEY } from './config'

const TOKEN_KEY = 'factory_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}
export function setToken(t) {
  localStorage.setItem(TOKEN_KEY, t)
}
export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

let onUnauthorized = null
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request(path, opts = {}) {
  let res
  try {
    res = await fetch(API_BASE + path, {
      ...opts,
      headers: {
        Authorization: `Bearer ${ANON_KEY}`,
        'x-factory-token': getToken(),
        'Content-Type': 'application/json',
      },
    })
  } catch {
    throw new ApiError(0, 'Network error — could not reach the factory API')
  }

  let data = null
  try {
    data = await res.json()
  } catch {
    // non-JSON body; leave data null
  }

  if (res.status === 401) {
    const err = new ApiError(401, (data && data.error) || 'Invalid factory token (401)')
    if (onUnauthorized) onUnauthorized(err)
    throw err
  }
  if (!res.ok) {
    throw new ApiError(res.status, (data && data.error) || `Request failed (${res.status})`)
  }
  return data
}

export const api = {
  get: (query) => request(query),
  post: (body) => request('', { method: 'POST', body: JSON.stringify(body) }),
}
