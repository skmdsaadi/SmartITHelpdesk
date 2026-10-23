import { useCallback, useEffect, useState } from 'react'

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) { super(message); this.status = status }
}

export async function api<T>(path: string, options: RequestInit = {}, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  const signal = options.signal ? AbortSignal.any([options.signal, controller.signal]) : controller.signal
  try {
    const response = await fetch('/api/v1' + path, {
      ...options, signal, credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', 'X-Helpdesk-Request': '1', ...options.headers },
    })
    const data = response.status === 204 ? null : await response.json().catch(() => null)
    if (!response.ok) {
      let message = typeof data?.detail === 'string' ? data.detail : response.status === 413
        ? 'The upload exceeds the 2 MiB limit. Choose a smaller file.' : 'Request failed. Please try again.'
      if (Array.isArray(data?.detail)) {
        message = data.detail.map((item: { loc?: string[]; msg?: string }) =>
          (item.loc?.slice(1).join('.') || 'Input') + ': ' + (item.msg || 'Invalid value')).join(' ')
      }
      if (response.status === 401 && !['/auth/login', '/auth/register', '/auth/me'].includes(path)) {
        window.dispatchEvent(new Event('helpdesk:unauthorized'))
      }
      throw new ApiError(message, response.status)
    }
    return data as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (options.signal?.aborted) throw error
    const write = options.method && options.method !== 'GET'
    throw new ApiError(write
      ? 'Connection interrupted. The action may have been saved. Refresh before submitting again.'
      : 'Cannot reach the helpdesk. Check the backend connection and try again.', 0)
  } finally { window.clearTimeout(timer) }
}

export function errorText(error: unknown) { return error instanceof Error ? error.message : 'Something went wrong.' }

export function useResource<T>(path: string) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(v => v + 1), [])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(''); setData(null)
    api<T>(path, { signal: controller.signal })
      .then(value => { if (!controller.signal.aborted) setData(value) })
      .catch(error => { if (!controller.signal.aborted) setError(errorText(error)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [path, revision])
  return { data, error, loading, refresh }
}
