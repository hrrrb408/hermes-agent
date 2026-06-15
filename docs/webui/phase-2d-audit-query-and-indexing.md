# Phase 2D — Audit Query + Indexing

## Read API (no new route)

The existing read-only route is enhanced in place:

```
GET /api/dev/v1/tools/audit-events
```

No new path is added. The route gains optional query parameters; when any new
filter is present (or an opaque cursor / `order=asc`), the durable-store query
engine serves the request. Legacy requests (`auditKind` + integer-offset cursor
+ `canonicalName`) keep using the legacy reader unchanged.

### New optional parameters

`order`, `eventType`, `toolId`, `status`, `source`, `providerMode`,
`readOnly`, `writeRequired`, `fromCreatedAt`, `toCreatedAt`, `search`,
`includeSummary`.

### Store-mode response shape

```json
{
  "items": [ ... ],
  "nextCursor": "<opaque> | null",
  "previousCursor": null,
  "hasMore": false,
  "limit": 50,
  "order": "desc",
  "query": { ...echoed safe filters... },
  "storeStatus": { "present": true, "segmentCount": 1, "schemaVersion": "audit_schema_v2" },
  "indexStatus": { "present": true, "consistent": true, "stale": false, ... },
  "schemaVersion": "audit_schema_v2",
  "skippedMalformed": 0
}
```

## Cursor pagination

Cursors are base64url JSON objects carrying `lastSequence`, `direction`,
`queryHash`, and `issuedAt`. They never carry a file path, an absolute path,
an index internal, a secret, or a full token hash.

- `queryHash` is a stable hash of the filter shape; a cursor whose hash does
  not match the current filters is rejected (`blocked_audit_cursor_query_mismatch`).
- Tampered / undecodable cursors are rejected (`blocked_audit_cursor_invalid`).
- Legacy integer-offset cursors remain accepted for backward compatibility.

## Index

Per-field indexes (`by-event-type.json`, …) accelerate equality lookups. The
**query engine treats a full segment scan as the source of truth** (robust to
rotation, corruption, and a stale / missing index). The index is an accelerator
and a status signal:

- `rebuild_audit_index()` — full scan rebuild.
- `update_audit_index_for_event()` — incremental update for one new event.
- `query_audit_index(field, value)` — equality lookup (returns `None` when the
  index is missing, so the caller falls back to scan).
- `validate_audit_index()` / `repair_audit_index_if_needed()` — consistency
  check + automatic rebuild when missing / stale / inconsistent.

The query engine opportunistically repairs a stale index before returning
`indexStatus`, so the Audit Viewer's index badge reflects reality.

## Filters + search

Equality filters: `eventType`, `toolId`, `status`, `auditKind`, `source`,
`providerMode`, `readOnly`, `writeRequired`.

Time range: `fromCreatedAt`, `toCreatedAt` (ISO-8601, inclusive, parsed to
aware datetimes for comparison).

Safe search: case-insensitive substring over `summary`, `safeMetadata`, and a
small set of safe scalar fields. Unsafe control characters and overly long
search strings are rejected.

## Limits

`limit` is validated 1..100 (FastAPI enforces the HTTP cap); the engine also
enforces `blocked_audit_limit_too_large` for callers that bypass the HTTP layer.
