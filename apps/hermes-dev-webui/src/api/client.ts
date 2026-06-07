/**
 * Unified Dev API client for the Hermes Dev WebUI.
 *
 * Provides typed fetch wrappers with timeout, abort, error parsing,
 * and request ID support. All API calls go through this module.
 */

/** Default API base URL — matches the Dev Web API server. */
const DEFAULT_BASE_URL = 'http://127.0.0.1:5181'

/** Request timeout in milliseconds. */
const DEFAULT_TIMEOUT_MS = 8_000

/** API error shape matching the backend ErrorResponse envelope. */
export interface DevApiError {
  readonly code: string
  readonly message: string
  readonly requestId?: string
  readonly status?: number
}

/** Parsed successful API response. */
export interface DevApiResponse<T> {
  readonly data: T
  readonly meta: {
    readonly requestId: string
    readonly timestamp: string
  }
}

/** Configuration for the API client. */
export interface DevApiClientConfig {
  readonly baseUrl: string
  readonly timeoutMs: number
}

/** Resolved client config with defaults applied. */
function resolveConfig(config?: Partial<DevApiClientConfig>): DevApiClientConfig {
  const baseUrl =
    config?.baseUrl ??
    (typeof import.meta !== 'undefined'
      ? (import.meta as Record<string, Record<string, string>>).env?.VITE_HERMES_DEV_API_BASE_URL
      : undefined) ??
    DEFAULT_BASE_URL

  return {
    baseUrl,
    timeoutMs: config?.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  }
}

/**
 * Parse an error from an API response.
 *
 * Tries to extract the structured error envelope. Falls back to a
 * generic error for non-JSON responses or network failures.
 */
function parseApiError(response: Response, body: string | null): DevApiError {
  if (body) {
    try {
      const parsed = JSON.parse(body) as {
        error?: { code?: string; message?: string }
        requestId?: string
      }
      if (parsed.error) {
        return {
          code: parsed.error.code ?? 'UNKNOWN_ERROR',
          message: parsed.error.message ?? 'An error occurred.',
          requestId: parsed.requestId,
          status: response.status,
        }
      }
    } catch {
      // Not JSON — fall through
    }
  }
  return {
    code: `HTTP_${response.status}`,
    message: `Request failed with status ${response.status}.`,
    status: response.status,
  }
}

/**
 * Make a typed GET request to the Dev API.
 *
 * @template T - The expected response data type.
 * @param path - API path relative to the base URL (e.g., '/sessions').
 * @param config - Optional client configuration override.
 * @param signal - Optional AbortSignal for request cancellation.
 * @returns Parsed response data and metadata.
 * @throws {DevApiError} On any error (network, HTTP, or business error).
 */
export async function apiGet<T>(
  path: string,
  config?: Partial<DevApiClientConfig>,
  signal?: AbortSignal,
): Promise<DevApiResponse<T>> {
  const { baseUrl, timeoutMs } = resolveConfig(config)

  const url = new URL(path, baseUrl)
  const requestId = crypto.randomUUID?.()?.replace(/-/g, '') ?? Date.now().toString(36)

  // Create timeout abort controller
  const timeoutController = new AbortController()
  const timeoutId = setTimeout(() => timeoutController.abort(), timeoutMs)

  // Combine signals: external signal + timeout
  let combinedSignal: AbortSignal
  if (signal) {
    // Forward external abort to timeout controller
    signal.addEventListener('abort', () => timeoutController.abort())
    combinedSignal = timeoutController.signal
  } else {
    combinedSignal = timeoutController.signal
  }

  try {
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'X-Request-ID': requestId,
      },
      signal: combinedSignal,
    })

    const text = await response.text()

    if (!response.ok) {
      throw parseApiError(response, text)
    }

    const parsed = JSON.parse(text) as DevApiResponse<T>
    return parsed
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      // Distinguish timeout from user-initiated abort
      if (signal?.aborted) {
        throw {
          code: 'REQUEST_CANCELLED',
          message: 'Request was cancelled.',
        } satisfies DevApiError
      }
      throw {
        code: 'REQUEST_TIMEOUT',
        message: 'Request timed out.',
      } satisfies DevApiError
    }

    // jsdom may throw a generic TypeError instead of DOMException for abort
    if (err instanceof TypeError && signal?.aborted) {
      throw {
        code: 'REQUEST_CANCELLED',
        message: 'Request was cancelled.',
      } satisfies DevApiError
    }

    // Re-throw if already a DevApiError
    if (err && typeof err === 'object' && 'code' in err && 'message' in err) {
      throw err
    }

    // Network error
    throw {
      code: 'NETWORK_ERROR',
      message: 'Unable to connect to the API.',
    } satisfies DevApiError
  } finally {
    clearTimeout(timeoutId)
  }
}

/**
 * Check if an error is a DevApiError.
 */
export function isDevApiError(err: unknown): err is DevApiError {
  return (
    err !== null &&
    err !== undefined &&
    typeof err === 'object' &&
    'code' in err &&
    'message' in err
  )
}

/** Get the default base URL (for testing). */
export function getDefaultBaseUrl(): string {
  return DEFAULT_BASE_URL
}
