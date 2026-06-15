/**
 * Shared Dev Console formatters (Phase 2E).
 *
 * Pure, side-effect-free helpers for rendering safe values in the unified
 * developer console. None of these ever surface raw secrets, full hashes, or
 * callable reprs — hash truncation is intentionally lossy.
 */

/**
 * Format a byte count as a compact human-readable string.
 *
 * Promoted from ToolPolicyOverview.vue so the new console sections share one
 * implementation. The original ToolPolicyOverview copy is intentionally left
 * in place (scope discipline — no refactor of existing tested panels in 2E).
 */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—'
  if (bytes < 1024) return `${bytes} bytes`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1_073_741_824) return `${(bytes / 1_048_576).toFixed(1)} MB`
  return `${(bytes / 1_073_741_824).toFixed(1)} GB`
}

/**
 * Truncate a digest/hash/id string for display. Returns '—' for empty input.
 * The full value is never rendered in the console UI (lossy by design).
 */
export function truncateHash(value: string | null | undefined, max = 16): string {
  if (value === null || value === undefined || value === '') return '—'
  if (value.length <= max) return value
  return `${value.slice(0, max)}…`
}

/**
 * Format an integer count, guarding against non-finite values.
 */
export function formatCount(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return '—'
  return String(n)
}

/**
 * Format an ISO timestamp as a short local-time string. Returns '—' for empty
 * or invalid input. Never throws.
 */
export function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  // ISO-ish short form, no timezone gymnastics — display only.
  const pad = (x: number): string => String(x).padStart(2, '0')
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())} ${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`
}

/**
 * Render a boolean flag as a short Yes/No label (used in summary cards).
 */
export function formatFlag(value: boolean | null | undefined): string {
  if (value === true) return 'Yes'
  if (value === false) return 'No'
  return '—'
}
