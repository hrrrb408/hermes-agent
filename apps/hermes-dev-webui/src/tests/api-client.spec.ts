/**
 * Tests for the Dev API client module.
 *
 * Covers URL construction, query encoding, response parsing,
 * error handling, timeout, and abort scenarios.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiGet, isDevApiError, getDefaultBaseUrl } from '@/api/client'
import type { DevApiError } from '@/api/client'

// ── Mock fetch ──

function mockFetchResponse(
  status: number,
  body: Record<string, unknown>,
  _headers: Record<string, string> = {},
): void {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Map(Object.entries(_headers)),
    text: () => Promise.resolve(JSON.stringify(body)),
  }))
}

function mockFetchError(error: Error): void {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(error))
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('apiGet', () => {
  it('makes GET request to the correct base URL', async () => {
    mockFetchResponse(200, {
      data: { items: [] },
      meta: { requestId: 'test-rid', timestamp: '2026-06-07T10:00:00Z' },
    })

    await apiGet('/sessions', { baseUrl: 'http://127.0.0.1:5181' })

    expect(fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:5181/sessions',
      expect.objectContaining({ method: 'GET' }),
    )
  })

  it('sends Accept and X-Request-ID headers', async () => {
    mockFetchResponse(200, {
      data: {},
      meta: { requestId: 'r1', timestamp: '2026-06-07T10:00:00Z' },
    })

    await apiGet('/status', { baseUrl: 'http://127.0.0.1:5181' })

    const callArgs = (fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit]
    expect(callArgs[1].headers).toHaveProperty('Accept', 'application/json')
    expect(callArgs[1].headers).toHaveProperty('X-Request-ID')
  })

  it('parses successful JSON response', async () => {
    const responseBody = {
      data: { id: 's1', title: 'Test' },
      meta: { requestId: 'abc123', timestamp: '2026-06-07T10:00:00Z' },
    }
    mockFetchResponse(200, responseBody)

    const result = await apiGet<{ id: string; title: string }>(
      '/sessions/s1',
      { baseUrl: 'http://127.0.0.1:5181' },
    )

    expect(result.data).toEqual({ id: 's1', title: 'Test' })
    expect(result.meta.requestId).toBe('abc123')
  })

  it('throws DevApiError on 400 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'INVALID_PARAMETER', message: 'Invalid limit.' },
        requestId: 'err-rid',
      })),
    }))

    try {
      await apiGet('/sessions?limit=0', { baseUrl: 'http://127.0.0.1:5181' })
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      const apiErr = err as DevApiError
      expect(apiErr.code).toBe('INVALID_PARAMETER')
      expect(apiErr.status).toBe(400)
    }
  })

  it('throws DevApiError on 404 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'SESSION_NOT_FOUND', message: 'Session was not found.' },
        requestId: 'err-rid',
      })),
    }))

    try {
      await apiGet('/sessions/nonexistent', { baseUrl: 'http://127.0.0.1:5181' })
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as DevApiError).code).toBe('SESSION_NOT_FOUND')
    }
  })

  it('throws DevApiError on 503 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      headers: new Map(),
      text: () => Promise.resolve(JSON.stringify({
        error: { code: 'SESSION_STORE_UNAVAILABLE', message: 'Session storage is unavailable.' },
        requestId: 'err-rid',
      })),
    }))

    try {
      await apiGet('/sessions', { baseUrl: 'http://127.0.0.1:5181' })
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as DevApiError).code).toBe('SESSION_STORE_UNAVAILABLE')
    }
  })

  it('throws NETWORK_ERROR on fetch failure', async () => {
    mockFetchError(new TypeError('Failed to fetch'))

    try {
      await apiGet('/sessions', { baseUrl: 'http://127.0.0.1:5181', timeoutMs: 1000 })
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as DevApiError).code).toBe('NETWORK_ERROR')
    }
  })

  it('throws REQUEST_CANCELLED when signal is aborted', async () => {
    const controller = new AbortController()
    controller.abort()

    try {
      await apiGet('/sessions', { baseUrl: 'http://127.0.0.1:5181' }, controller.signal)
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as DevApiError).code).toBe('REQUEST_CANCELLED')
    }
  })

  it('handles non-JSON error response gracefully', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      headers: new Map(),
      text: () => Promise.resolve('Internal Server Error'),
    }))

    try {
      await apiGet('/sessions', { baseUrl: 'http://127.0.0.1:5181' })
      expect.fail('Should have thrown')
    } catch (err) {
      expect(isDevApiError(err)).toBe(true)
      expect((err as DevApiError).code).toBe('HTTP_500')
    }
  })
})

describe('isDevApiError', () => {
  it('returns true for DevApiError objects', () => {
    expect(isDevApiError({ code: 'TEST', message: 'test' })).toBe(true)
  })

  it('returns false for null', () => {
    expect(isDevApiError(null)).toBe(false)
  })

  it('returns false for strings', () => {
    expect(isDevApiError('error')).toBe(false)
  })
})

describe('getDefaultBaseUrl', () => {
  it('returns 127.0.0.1:5181', () => {
    expect(getDefaultBaseUrl()).toBe('http://127.0.0.1:5181')
  })
})
