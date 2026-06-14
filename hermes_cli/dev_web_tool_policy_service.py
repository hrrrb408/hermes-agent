"""Dev Web API Tool Policy Read-Only Query Service.

Pure-computation query service that reads from the static tool policy module
(dev_web_tool_policy) and adapts the data into DTOs for the Tool Policy
read-only API. All queries are side-effect-free.

Safety guarantees:
  - Single source of truth: hermes_cli.dev_web_tool_policy
  - Never imports tools.registry, any Tool Handler, SessionDB, Provider,
    Agent, Memory Writer, Review Queue, or FastAPI.
  - Never accesses filesystem, database, or network.
  - Never creates threads, caches, locks, or mutable global state.
  - All DTO fields are whitelisted; forbidden fields never appear.
  - rationalePreview is truncated to 200 chars and redacted for paths/secrets.

Phase: 1G-02A — Tool Policy Read-Only Query Service and DTO Implementation
Status: Read-only service layer (no FastAPI route)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from hermes_cli.dev_web_tool_policy import (
    ALL_CANONICAL_TOOLS,
    CANDIDATE_ALLOWLIST,
    MAX_AGENT_VISIBLE_OUTPUT_BYTES,
    MAX_ARGUMENT_ARRAY_LENGTH,
    MAX_ARGUMENT_NESTING_DEPTH,
    MAX_ARGUMENT_PAYLOAD_BYTES,
    MAX_ARGUMENT_STRING_LENGTH,
    DEFAULT_R0_TIMEOUT_SECONDS,
    DEFAULT_R1_TIMEOUT_SECONDS,
    MAX_GLOBAL_TOOL_CONCURRENCY,
    MAX_SERIALIZED_OUTPUT_BYTES,
    MAX_TOOL_CALLS_PER_RUN,
    MAX_TOOL_CONCURRENCY_PER_RUN,
    MAX_TOOL_TIMEOUT_SECONDS,
    MAX_WEB_PREVIEW_OUTPUT_BYTES,
    RISK_RANK,
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    TOOLS_BY_RISK,
    ToolCapability,
    ToolPolicyEntry,
    ToolRiskLevel,
    get_all_tool_policies,
)


# ---------------------------------------------------------------------------
# 1. Path and secret redaction
# ---------------------------------------------------------------------------

_RE_MACOS_PATH = re.compile(r"/Users/[^\s\"'`\)\]]+")
_RE_LINUX_PATH = re.compile(r"/home/[^\s\"'`\)\]]+")
_RE_FILE_URI = re.compile(r"file://[^\s\"'`\)\]]+")
_RE_WINDOWS_PATH = re.compile(r"[A-Z]:\\[^\s\"'`\)\]]+", re.IGNORECASE)

# Secret patterns
_RE_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r'api_key\s*=\s*\S+', re.IGNORECASE), 'api_key=[secret-redacted]'),
    (re.compile(r'api_key["\']?\s*:\s*["\']?\S+', re.IGNORECASE), 'api_key: [secret-redacted]'),
    (re.compile(r'token\s*=\s*\S+', re.IGNORECASE), 'token=[secret-redacted]'),
    (re.compile(r'password\s*=\s*\S+', re.IGNORECASE), 'password=[secret-redacted]'),
    (re.compile(r'secret\s*=\s*\S+', re.IGNORECASE), 'secret=[secret-redacted]'),
    (re.compile(r'bearer\s+\S+', re.IGNORECASE), 'bearer [secret-redacted]'),
    (re.compile(r'authorization\s*:\s*\S+', re.IGNORECASE), 'authorization: [secret-redacted]'),
]

_RATIONALE_PREVIEW_MAX_LENGTH = 200


def _redact_paths_and_secrets(text: str) -> str:
    """Redact local file paths, file:// URIs, and secret patterns from text."""
    if not text:
        return text

    # Redact file:// URIs first
    text = _RE_FILE_URI.sub("[file-uri-redacted]", text)

    # Redact macOS and Linux absolute paths
    text = _RE_MACOS_PATH.sub("[local-path]", text)
    text = _RE_LINUX_PATH.sub("[local-path]", text)

    # Redact Windows absolute paths
    text = _RE_WINDOWS_PATH.sub("[local-path]", text)

    # Redact secrets
    for pattern, replacement in _RE_SECRET_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


def _truncate_rationale(text: str, max_length: int = _RATIONALE_PREVIEW_MAX_LENGTH) -> str:
    """Truncate rationale to max_length chars and redact paths/secrets."""
    if not text:
        return text
    # Redact first, then truncate
    redacted = _redact_paths_and_secrets(text)
    # Remove newlines and stack traces
    redacted = redacted.replace("\n", " ").replace("\r", " ")
    if len(redacted) > max_length:
        redacted = redacted[:max_length]
    return redacted


# ---------------------------------------------------------------------------
# 2. Sort enum
# ---------------------------------------------------------------------------


class ToolCatalogSort(str, Enum):
    """Allowed sort orders for the tool catalog."""

    NAME_ASC = "nameAsc"
    NAME_DESC = "nameDesc"
    RISK_ASC = "riskAsc"
    RISK_DESC = "riskDesc"


# ---------------------------------------------------------------------------
# 3. Policy status enum
# ---------------------------------------------------------------------------


class ToolPolicyStatus(str, Enum):
    """Derived policy status for a tool."""

    PERMANENTLY_DENIED = "PERMANENTLY_DENIED"
    CANDIDATE = "CANDIDATE"
    UNLISTED = "UNLISTED"
    STATICALLY_ALLOWED = "STATICALLY_ALLOWED"


def _derive_policy_status(entry: ToolPolicyEntry) -> ToolPolicyStatus:
    """Derive the policy status from a ToolPolicyEntry.

    Priority: PERMANENTLY_DENIED > STATICALLY_ALLOWED > CANDIDATE > UNLISTED
    """
    if entry.permanently_denied:
        return ToolPolicyStatus.PERMANENTLY_DENIED
    if entry.statically_allowed:
        return ToolPolicyStatus.STATICALLY_ALLOWED
    if entry.candidate_allowlisted:
        return ToolPolicyStatus.CANDIDATE
    return ToolPolicyStatus.UNLISTED


# ---------------------------------------------------------------------------
# 4. DTOs — frozen dataclasses (no Pydantic dependency)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolPolicyExecutionDTO:
    """Execution capability status (all false)."""

    implemented: bool
    enabled: bool
    provider_schema_sent: bool
    dispatch_available: bool
    audit_available: bool


@dataclass(frozen=True, slots=True)
class ToolPolicySafetyDTO:
    """Safety flags (all read-only, no side effects)."""

    read_only: bool
    side_effects: bool
    write_enabled: bool
    execute_available: bool
    policy_mutation_available: bool


@dataclass(frozen=True, slots=True)
class ToolPolicyLimitsDTO:
    """Global limits from the static policy module."""

    max_argument_payload_bytes: int
    max_argument_nesting_depth: int
    max_argument_string_length: int
    max_argument_array_length: int
    default_r0_timeout_seconds: int
    default_r1_timeout_seconds: int
    max_tool_timeout_seconds: int
    max_tool_calls_per_run: int
    max_global_concurrency: int
    max_concurrency_per_run: int
    max_serialized_output_bytes: int
    max_agent_visible_output_bytes: int
    max_web_preview_output_bytes: int


@dataclass(frozen=True, slots=True)
class ToolPolicyStatusDTO:
    """Complete policy status response DTO."""

    mode: str
    inventory_count: int
    risk_counts: dict[str, int]
    permanent_denylist_count: int
    candidate_allowlist_count: int
    enabled_allowlist_count: int
    execution: ToolPolicyExecutionDTO
    limits: ToolPolicyLimitsDTO
    safety: ToolPolicySafetyDTO


@dataclass(frozen=True, slots=True)
class ToolCatalogItemDTO:
    """Single tool entry in the catalog response."""

    canonical_name: str
    primary_risk: str
    risk_rank: str
    capabilities: tuple[str, ...]
    permanently_denied: bool
    candidate_allowlisted: bool
    statically_allowed: bool
    allowed: bool
    policy_status: str
    reason_code: str
    source_module: str
    rationale_preview: str
    execution_available: bool
    schema_preview_available: bool
    dry_run_available: bool


@dataclass(frozen=True, slots=True)
class ToolCatalogSummaryDTO:
    """Summary counts in catalog response."""

    inventory_count: int
    permanent_denylist_count: int
    candidate_allowlist_count: int
    enabled_allowlist_count: int


@dataclass(frozen=True, slots=True)
class ToolCatalogSafetyDTO:
    """Safety flags in catalog response."""

    read_only: bool
    side_effects: bool
    execute_available: bool


@dataclass(frozen=True, slots=True)
class ToolCatalogFiltersDTO:
    """Active filters applied in the catalog query."""

    q: str | None
    risk: str | None
    capability: str | None
    policy_status: str | None
    sort: str


@dataclass(frozen=True, slots=True)
class ToolCatalogResponseDTO:
    """Complete catalog response DTO."""

    items: tuple[ToolCatalogItemDTO, ...]
    page: int
    page_size: int
    total: int
    total_pages: int
    filters: ToolCatalogFiltersDTO
    summary: ToolCatalogSummaryDTO
    safety: ToolCatalogSafetyDTO


# ---------------------------------------------------------------------------
# 5. Query / Filter DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolCatalogQuery:
    """Validated query parameters for the tool catalog."""

    q: str | None = None
    risk: ToolRiskLevel | None = None
    capability: ToolCapability | None = None
    policy_status: ToolPolicyStatus | None = None
    page: int = 1
    page_size: int = 25
    sort: ToolCatalogSort = ToolCatalogSort.NAME_ASC


# ---------------------------------------------------------------------------
# 6. Validation errors
# ---------------------------------------------------------------------------


class ToolPolicyQueryError(Exception):
    """Base error for tool policy query validation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class InvalidToolPolicyQueryError(ToolPolicyQueryError):
    """Invalid search query."""

    def __init__(self, message: str = "Invalid tool policy query") -> None:
        super().__init__("INVALID_TOOL_POLICY_QUERY", message)


class InvalidToolRiskError(ToolPolicyQueryError):
    """Invalid risk parameter."""

    def __init__(self, message: str = "Risk must be one of: R0, R1, R2, R3, R4, R5") -> None:
        super().__init__("INVALID_TOOL_RISK", message)


class InvalidToolCapabilityError(ToolPolicyQueryError):
    """Invalid capability parameter."""

    def __init__(self, message: str = "Invalid tool capability value") -> None:
        super().__init__("INVALID_TOOL_CAPABILITY", message)


class InvalidToolPolicyStatusError(ToolPolicyQueryError):
    """Invalid policy status parameter."""

    def __init__(self, message: str = "Policy status must be one of: PERMANENTLY_DENIED, CANDIDATE, UNLISTED, STATICALLY_ALLOWED") -> None:
        super().__init__("INVALID_TOOL_POLICY_STATUS", message)


class InvalidToolSortError(ToolPolicyQueryError):
    """Invalid sort parameter."""

    def __init__(self, message: str = "Sort must be one of: nameAsc, nameDesc, riskAsc, riskDesc") -> None:
        super().__init__("INVALID_TOOL_SORT", message)


class ToolPolicyDataInvalidError(ToolPolicyQueryError):
    """Policy data failed internal integrity check."""

    def __init__(self, message: str = "Tool policy data integrity check failed") -> None:
        super().__init__("TOOL_POLICY_DATA_INVALID", message)


# ---------------------------------------------------------------------------
# 7. Allowed values for validation
# ---------------------------------------------------------------------------

_VALID_RISK_VALUES: frozenset[str] = frozenset(r.value for r in ToolRiskLevel)
_VALID_CAPABILITY_VALUES: frozenset[str] = frozenset(c.value for c in ToolCapability)
_VALID_POLICY_STATUS_VALUES: frozenset[str] = frozenset(s.value for s in ToolPolicyStatus)
_VALID_SORT_VALUES: frozenset[str] = frozenset(s.value for s in ToolCatalogSort)

_DANGEROUS_PARAM_NAMES: frozenset[str] = frozenset({
    "execute", "force", "enable", "write", "dispatch", "override",
})

_MAX_QUERY_LENGTH = 120
_DEFAULT_PAGE_SIZE = 25
_MIN_PAGE_SIZE = 1
_MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# 8. Query validation
# ---------------------------------------------------------------------------


def validate_catalog_query(
    q: str | None = None,
    risk: str | None = None,
    capability: str | None = None,
    policy_status: str | None = None,
    page: int = 1,
    page_size: int = _DEFAULT_PAGE_SIZE,
    sort: str = "nameAsc",
    extra_params: dict[str, Any] | None = None,
) -> ToolCatalogQuery:
    """Validate and parse catalog query parameters.

    Returns a ToolCatalogQuery on success, raises ToolPolicyQueryError on
    invalid input.
    """
    # Check for dangerous extra parameters
    if extra_params:
        for key in extra_params:
            if key.lower() in _DANGEROUS_PARAM_NAMES:
                raise InvalidToolPolicyQueryError(
                    f"Dangerous query parameter rejected: {key}"
                )

    # Validate q
    if q is not None:
        if len(q) > _MAX_QUERY_LENGTH:
            raise InvalidToolPolicyQueryError(
                f"Query string exceeds maximum length of {_MAX_QUERY_LENGTH} characters"
            )

    # Validate risk
    parsed_risk: ToolRiskLevel | None = None
    if risk is not None:
        if risk not in _VALID_RISK_VALUES:
            raise InvalidToolRiskError()
        parsed_risk = ToolRiskLevel(risk)

    # Validate capability
    parsed_capability: ToolCapability | None = None
    if capability is not None:
        if capability not in _VALID_CAPABILITY_VALUES:
            raise InvalidToolCapabilityError()
        parsed_capability = ToolCapability(capability)

    # Validate policy_status
    parsed_policy_status: ToolPolicyStatus | None = None
    if policy_status is not None:
        if policy_status not in _VALID_POLICY_STATUS_VALUES:
            raise InvalidToolPolicyStatusError()
        parsed_policy_status = ToolPolicyStatus(policy_status)

    # Validate page
    if page < 1:
        raise InvalidToolPolicyQueryError("Page must be >= 1")

    # Validate page_size
    if page_size < _MIN_PAGE_SIZE or page_size > _MAX_PAGE_SIZE:
        raise InvalidToolPolicyQueryError(
            f"Page size must be between {_MIN_PAGE_SIZE} and {_MAX_PAGE_SIZE}"
        )

    # Validate sort
    if sort not in _VALID_SORT_VALUES:
        raise InvalidToolSortError()
    parsed_sort = ToolCatalogSort(sort)

    return ToolCatalogQuery(
        q=q,
        risk=parsed_risk,
        capability=parsed_capability,
        policy_status=parsed_policy_status,
        page=page,
        page_size=page_size,
        sort=parsed_sort,
    )


# ---------------------------------------------------------------------------
# 9. DTO builders
# ---------------------------------------------------------------------------


def _build_catalog_item_dto(entry: ToolPolicyEntry) -> ToolCatalogItemDTO:
    """Build a single catalog item DTO from a ToolPolicyEntry."""
    # Derive reason code
    if entry.permanently_denied:
        reason_code = "TOOL_PERMANENTLY_DENIED"
    elif entry.statically_allowed:
        reason_code = "TOOL_ALLOWED"
    elif entry.candidate_allowlisted:
        reason_code = "TOOL_CANDIDATE"
    else:
        reason_code = "TOOL_NOT_ALLOWED"

    return ToolCatalogItemDTO(
        canonical_name=entry.canonical_name,
        primary_risk=entry.primary_risk.name,  # "R0", "R1", etc.
        risk_rank=entry.primary_risk.value,
        capabilities=tuple(sorted(c.value for c in entry.capabilities)),
        permanently_denied=entry.permanently_denied,
        candidate_allowlisted=entry.candidate_allowlisted,
        statically_allowed=entry.statically_allowed,
        allowed=False,  # Catalog never vouches executability; STATIC_ALLOWLIST gates the execute route.
        policy_status=_derive_policy_status(entry).value,
        reason_code=reason_code,
        source_module=entry.source,
        rationale_preview=_truncate_rationale(entry.rationale),
        execution_available=False,
        schema_preview_available=False,
        dry_run_available=False,
    )


# ---------------------------------------------------------------------------
# 10. Service class
# ---------------------------------------------------------------------------


class DevToolPolicyQueryService:
    """Read-only query service for Tool Policy data.

    Single source of truth: hermes_cli.dev_web_tool_policy

    This service:
      - Reads ONLY from the static, immutable policy module
      - Produces whitelisted DTOs with path and secret redaction
      - Supports filtering, sorting, and pagination
      - Has zero side effects (no I/O, no state mutation)
      - Does not import or initialize Registry, Handler, Provider, SessionDB
    """

    def get_policy_status(self) -> ToolPolicyStatusDTO:
        """Return the complete policy status DTO.

        All values are derived from the static policy module.
        """
        # Risk counts from single source of truth
        risk_counts = {
            risk.value: len(TOOLS_BY_RISK[risk])
            for risk in ToolRiskLevel
        }

        return ToolPolicyStatusDTO(
            mode="DEFAULT_DENY",
            inventory_count=len(TOOL_POLICY_INVENTORY),
            risk_counts=risk_counts,
            permanent_denylist_count=len(STATIC_DENYLIST),
            candidate_allowlist_count=len(CANDIDATE_ALLOWLIST),
            enabled_allowlist_count=len(STATIC_ALLOWLIST),
            execution=ToolPolicyExecutionDTO(
                implemented=False,
                enabled=False,
                provider_schema_sent=False,
                dispatch_available=False,
                audit_available=False,
            ),
            limits=ToolPolicyLimitsDTO(
                max_argument_payload_bytes=MAX_ARGUMENT_PAYLOAD_BYTES,
                max_argument_nesting_depth=MAX_ARGUMENT_NESTING_DEPTH,
                max_argument_string_length=MAX_ARGUMENT_STRING_LENGTH,
                max_argument_array_length=MAX_ARGUMENT_ARRAY_LENGTH,
                default_r0_timeout_seconds=DEFAULT_R0_TIMEOUT_SECONDS,
                default_r1_timeout_seconds=DEFAULT_R1_TIMEOUT_SECONDS,
                max_tool_timeout_seconds=MAX_TOOL_TIMEOUT_SECONDS,
                max_tool_calls_per_run=MAX_TOOL_CALLS_PER_RUN,
                max_global_concurrency=MAX_GLOBAL_TOOL_CONCURRENCY,
                max_concurrency_per_run=MAX_TOOL_CONCURRENCY_PER_RUN,
                max_serialized_output_bytes=MAX_SERIALIZED_OUTPUT_BYTES,
                max_agent_visible_output_bytes=MAX_AGENT_VISIBLE_OUTPUT_BYTES,
                max_web_preview_output_bytes=MAX_WEB_PREVIEW_OUTPUT_BYTES,
            ),
            safety=ToolPolicySafetyDTO(
                read_only=True,
                side_effects=False,
                write_enabled=False,
                execute_available=False,
                policy_mutation_available=False,
            ),
        )

    def list_tool_catalog(
        self,
        query: ToolCatalogQuery,
    ) -> ToolCatalogResponseDTO:
        """Return a filtered, sorted, paginated tool catalog.

        All items have allowed=False and all execution flags are False.
        Page beyond totalPages returns empty items (not an error).
        """
        # Build DTOs for all tools
        all_items = [
            _build_catalog_item_dto(entry)
            for entry in get_all_tool_policies()
        ]

        # Apply filters
        filtered = all_items

        # Search filter (q)
        if query.q is not None:
            q_lower = query.q.lower()
            filtered = [
                item for item in filtered
                if q_lower in item.canonical_name.lower()
                or q_lower in item.rationale_preview.lower()
            ]

        # Risk filter
        if query.risk is not None:
            risk_val = query.risk.value
            filtered = [
                item for item in filtered
                if item.risk_rank == risk_val
            ]

        # Capability filter
        if query.capability is not None:
            cap_val = query.capability.value
            filtered = [
                item for item in filtered
                if cap_val in item.capabilities
            ]

        # Policy status filter
        if query.policy_status is not None:
            status_val = query.policy_status.value
            filtered = [
                item for item in filtered
                if item.policy_status == status_val
            ]

        total = len(filtered)

        # Sort
        if query.sort == ToolCatalogSort.NAME_ASC:
            filtered.sort(key=lambda i: i.canonical_name)
        elif query.sort == ToolCatalogSort.NAME_DESC:
            filtered.sort(key=lambda i: i.canonical_name, reverse=True)
        elif query.sort == ToolCatalogSort.RISK_ASC:
            filtered.sort(key=lambda i: (RISK_RANK[ToolRiskLevel(i.risk_rank)], i.canonical_name))
        elif query.sort == ToolCatalogSort.RISK_DESC:
            filtered.sort(key=lambda i: (-RISK_RANK[ToolRiskLevel(i.risk_rank)], i.canonical_name))

        # Pagination
        total_pages = max(1, math.ceil(total / query.page_size))
        start = (query.page - 1) * query.page_size
        end = start + query.page_size
        page_items = filtered[start:end]

        return ToolCatalogResponseDTO(
            items=tuple(page_items),
            page=query.page,
            page_size=query.page_size,
            total=total,
            total_pages=total_pages,
            filters=ToolCatalogFiltersDTO(
                q=query.q,
                risk=query.risk.value if query.risk else None,
                capability=query.capability.value if query.capability else None,
                policy_status=query.policy_status.value if query.policy_status else None,
                sort=query.sort.value,
            ),
            summary=ToolCatalogSummaryDTO(
                inventory_count=len(TOOL_POLICY_INVENTORY),
                permanent_denylist_count=len(STATIC_DENYLIST),
                candidate_allowlist_count=len(CANDIDATE_ALLOWLIST),
                enabled_allowlist_count=len(STATIC_ALLOWLIST),
            ),
            safety=ToolCatalogSafetyDTO(
                read_only=True,
                side_effects=False,
                execute_available=False,
            ),
        )
