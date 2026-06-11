/**
 * TypeScript types for the Dev API tool schema preview endpoints.
 *
 * Matches the Phase 1G-03 read-only Schema Preview contract.
 * All fields are read-only — preview ≠ execution.
 * No execute, dry-run, provider-send, or dispatch fields exist.
 */

// ── Enum-like union types ──

/** Schema preview redaction status — matches backend redaction constants. */
export type SchemaPreviewRedactionStatus =
  | 'clean'
  | 'redacted'
  | 'unavailable'

/** Schema preview reason code for unavailable tools. */
export type SchemaPreviewReasonCode =
  | 'AVAILABLE'
  | 'AVAILABLE_WITH_REDACTION'
  | 'RISK_R4_EXECUTION'
  | 'RISK_R5_SYSTEM'
  | 'PERMANENTLY_DENIED'
  | 'UNLISTED'
  | 'UNAVAILABLE_EMPTY_SCHEMA'
  | 'UNAVAILABLE_INVALID_SCHEMA'
  | 'UNAVAILABLE_SCHEMA_SOURCE_ERROR'

/** Schema shape detection — matches backend _detect_schema_shape(). */
export type SchemaPreviewShape =
  | 'object'
  | 'array'
  | 'primitive'
  | 'unknown'

/** Lookup result reason code. */
export type SchemaPreviewLookupReason =
  | 'FOUND'
  | 'NOT_FOUND'

// ── Field DTO ──

/** Single field within a tool schema preview — matches SchemaPreviewFieldDTO. */
export interface ToolSchemaPreviewField {
  readonly fieldName: string
  readonly fieldType: string
  readonly required: boolean
  readonly descriptionPreview: string | null
  readonly enumPreview: readonly string[] | null
  readonly defaultPresence: boolean
  readonly constraintsPreview: string | null
}

// ── Tool Schema Preview Item ──

/** Single tool schema preview — matches ToolSchemaPreviewItem. */
export interface ToolSchemaPreviewItem {
  readonly canonicalName: string
  readonly risk: string
  readonly capabilities: readonly string[]
  readonly schemaPreviewAvailable: boolean
  readonly schemaShape: SchemaPreviewShape
  readonly inputFields: readonly ToolSchemaPreviewField[]
  readonly redactionStatus: SchemaPreviewRedactionStatus
  readonly reasonCode: string
  readonly unavailableReason: string | null
}

// ── Catalog Response ──

/** Catalog data — matches ToolSchemaPreviewCatalogData. */
export interface ToolSchemaPreviewCatalogData {
  readonly totalCount: number
  readonly availableCount: number
  readonly unavailableCount: number
  readonly items: readonly ToolSchemaPreviewItem[]
}

/** Catalog response — GET /api/dev/v1/tools/schemas. */
export interface ToolSchemaPreviewCatalogResponse {
  readonly data: ToolSchemaPreviewCatalogData
  readonly meta: {
    readonly requestId: string
    readonly timestamp: string
  }
}

// ── Lookup Response ──

/** Lookup data — matches ToolSchemaPreviewLookupData. */
export interface ToolSchemaPreviewLookupData {
  readonly found: boolean
  readonly preview: ToolSchemaPreviewItem | null
  readonly reasonCode: SchemaPreviewLookupReason
}

/** Lookup response — GET /api/dev/v1/tools/schemas/{canonicalName}. */
export interface ToolSchemaPreviewLookupResponse {
  readonly data: ToolSchemaPreviewLookupData
  readonly meta: {
    readonly requestId: string
    readonly timestamp: string
  }
}
