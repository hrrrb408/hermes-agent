/**
 * Type definitions for the Phase 2B Provider Schema / API round-trip.
 *
 * Models the controlled Provider round-trip response returned by
 * POST /api/dev/v1/tools/execute with body.mode='provider_roundtrip'.
 *
 * Safety:
 *   - No API key, raw token, full tokenHash, raw arguments, or secret ever
 *     appears in these types. The backend redacts everything before return.
 *   - Real provider mode is blocked by default; the UI never accepts an API
 *     key input.
 */

/** Controlled provider mode. */
export type ProviderMode = 'disabled' | 'fake' | 'real'

/** One provider-emitted tool call (validated by the round-trip). */
export interface ProviderToolCallView {
  readonly id: string
  readonly name: string
  readonly arguments: Record<string, unknown>
  readonly status: string
  readonly blockedReason: string | null
}

/** One executed (or blocked) provider tool call result. */
export interface ProviderToolResultView {
  readonly toolCallId: string
  readonly toolId: string
  readonly status: string
  readonly executed: boolean
  readonly blockedReason: string | null
  readonly executeResult?: unknown
  readonly internalConfirmation?: boolean
  readonly readOnlyOnly?: boolean
}

/** Provider schema summary (counts only). */
export interface ProviderSchemaSummary {
  readonly schemaVersion: number
  readonly bundleVersion: number
  readonly toolCount: number
  readonly toolIds: readonly string[]
  readonly readOnlyOnly: boolean
  readonly writeToolCount: number
  readonly providerRecursiveToolCount: number
}

/** Safe provider round-trip response data. */
export interface ProviderRoundtripResultData {
  readonly status: 'completed' | 'blocked'
  readonly mode: 'provider_roundtrip'
  readonly providerMode: ProviderMode
  readonly providerRequestId: string
  readonly providerResponseId: string | null
  readonly providerSchemaSent: boolean
  readonly providerApiCalled: boolean
  readonly externalNetworkCalled: boolean
  readonly readOnlyOnly: boolean
  readonly toolWriteDisabled: boolean
  readonly toolCalls: readonly ProviderToolCallView[]
  readonly toolResults: readonly ProviderToolResultView[]
  readonly finalAnswer: string
  readonly providerAuditIds: readonly string[]
  readonly blockedReason: string | null
  readonly schemaSummary: ProviderSchemaSummary
}

/** Request body for the provider round-trip branch of the execute route. */
export interface ProviderRoundtripRequest {
  readonly mode: 'provider_roundtrip'
  readonly providerMode: ProviderMode
  readonly message: string
  readonly allowedToolIds?: readonly string[]
}

/**
 * Phase 3B-Live-Enablement: the strict manual one-shot live gate status.
 *
 * Surfaced by GET /api/dev/v1/status as data.providerBoundary.providerLive.
 * Value-free only — never an API-key value, Authorization header, raw token,
 * raw prompt/response secret, or callable repr. Live provider stays disabled
 * by default; the UI never accepts an API-key input.
 */
export interface ProviderLiveStatus {
  readonly liveEnabled: boolean
  readonly available: boolean
  readonly approvalRequired: boolean
  readonly approvalPresent: boolean
  readonly approvalCount: number
  readonly approvalSingleUse: boolean
  readonly approvalTtlSeconds: number
  readonly killSwitchActive: boolean
  readonly killSwitchTriggeredBy: string
  readonly toolExecutionDisabled: boolean
  readonly providerWriteBlocked: boolean
  readonly providerAutoWriteBlocked: boolean
  readonly autonomousWriteBlocked: boolean
  readonly productionRolloutBlocked: boolean
  readonly streamingBlocked: boolean
  readonly multiProviderBlocked: boolean
  readonly manualOneShot: boolean
  readonly budget: ProviderLiveBudgetBadge
  readonly redactionApplied: boolean
}

/** Value-free live budget badge (caps + remaining; never a key). */
export interface ProviderLiveBudgetBadge {
  readonly available: boolean
  readonly maxRequests: number
  readonly maxTotalTokens: number
  readonly maxInputTokens: number
  readonly maxOutputTokens: number
  readonly maxBudgetCents: number
  readonly maxRuntimeSeconds: number
  readonly maxRetries: number
  readonly rateLimitWindow: number
  readonly failClosedOnCounterError: boolean
  readonly requestsUsed?: number
  readonly tokensUsed?: number
  readonly centsUsed?: number
  readonly remainingCents?: number
  readonly remainingRequests?: number
  readonly windowMinute?: string
  readonly redactionApplied?: boolean
}

/**
 * Phase 3B: real-provider boundary safe-metadata block.
 *
 * Surfaced by GET /api/dev/v1/status as data.providerBoundary. Value-free
 * only — never an API-key value, never an Authorization header, never a raw
 * secret, never a full tokenHash. The UI renders this as a boundary status
 * badge. Real provider stays disabled by default.
 */
export interface ProviderBoundaryStatus {
  readonly providerMode: ProviderMode
  readonly apiEnabled: boolean
  readonly providerName: string
  readonly providerNameImplemented: boolean
  readonly baseUrlHost: string
  readonly baseUrlAllowed: boolean
  readonly model: string
  readonly modelAllowed: boolean
  readonly timeoutSeconds: number
  readonly maxRetries: number
  readonly dailyBudgetCents: number
  readonly maxTokens: number
  readonly perMinuteRequestCap: number
  readonly dailyRequestCap: number
  readonly dailyTokenCap: number
  /** Value-free: 'env' only. */
  readonly apiKeySource: 'env'
  /** Value-free: env_present / env_missing. */
  readonly apiKeyPresent: boolean
  readonly apiKeySourceDetail: 'env_present' | 'env_missing'
  readonly isDevHome: boolean
  /** True only when EVERY eligibility gate passes (live PID gate included). */
  readonly realReachable: boolean
  readonly gatingReason: string | null
  readonly providerWriteBlocked: boolean
  readonly providerAutoWriteBlocked: boolean
  readonly autonomousWriteBlocked: boolean
  readonly productionRolloutBlocked: boolean
  readonly redactionApplied: boolean
  /** Phase 3B-Live-Enablement: the strict manual one-shot live gate. */
  readonly providerLive: ProviderLiveStatus
}

/** Safe provider-boundary status returned by GET /status (data.providerBoundary). */
export interface SystemStatusData {
  readonly environment: string
  readonly apiVersion: string
  readonly status: string
  readonly readOnly: boolean
  readonly providerBoundary: ProviderBoundaryStatus
}
