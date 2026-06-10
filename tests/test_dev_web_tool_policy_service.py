"""Tests for hermes_cli.dev_web_tool_policy_service — read-only query service.

Phase 1G-02A: Tool Policy Read-Only Query Service and DTO Implementation.

All tests use the pure in-memory static policy module. No real tool execution,
filesystem access, database access, network access, Registry initialization,
Handler initialization, Provider initialization, or SessionDB access.
"""

from __future__ import annotations

import math
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import get_type_hints

import pytest

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
    STATIC_ALLOWLIST,
    STATIC_DENYLIST,
    TOOL_POLICY_INVENTORY,
    TOOLS_BY_RISK,
    ToolCapability,
    ToolRiskLevel,
)
from hermes_cli.dev_web_tool_policy_service import (
    DevToolPolicyQueryService,
    InvalidToolCapabilityError,
    InvalidToolPolicyQueryError,
    InvalidToolPolicyStatusError,
    InvalidToolRiskError,
    InvalidToolSortError,
    ToolCatalogFiltersDTO,
    ToolCatalogItemDTO,
    ToolCatalogQuery,
    ToolCatalogResponseDTO,
    ToolCatalogSafetyDTO,
    ToolCatalogSort,
    ToolCatalogSummaryDTO,
    ToolPolicyDataInvalidError,
    ToolPolicyExecutionDTO,
    ToolPolicyLimitsDTO,
    ToolPolicyQueryError,
    ToolPolicySafetyDTO,
    ToolPolicyStatus,
    ToolPolicyStatusDTO,
    _MAX_QUERY_LENGTH,
    _redact_paths_and_secrets,
    _truncate_rationale,
    validate_catalog_query,
)


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def service() -> DevToolPolicyQueryService:
    """Provide a fresh service instance."""
    return DevToolPolicyQueryService()


# ===================================================================
# 1. Policy Status — Exact Numbers
# ===================================================================


class TestPolicyStatusNumbers:
    """Policy Status DTO returns exact counts."""

    def test_inventory_count_is_71(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.inventory_count == 71

    def test_permanent_denylist_count_is_26(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.permanent_denylist_count == 26

    def test_candidate_allowlist_count_is_6(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.candidate_allowlist_count == 6

    def test_enabled_allowlist_count_is_0(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.enabled_allowlist_count == 0


# ===================================================================
# 2. Risk Counts — Exact
# ===================================================================


class TestRiskCounts:
    """Risk distribution is exact."""

    def test_r0_is_1(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R0"] == 1

    def test_r1_is_5(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R1"] == 5

    def test_r2_is_19(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R2"] == 19

    def test_r3_is_26(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R3"] == 26

    def test_r4_is_17(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R4"] == 17

    def test_r5_is_3(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.risk_counts["R5"] == 3

    def test_risk_counts_sum_to_71(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert sum(status.risk_counts.values()) == 71


# ===================================================================
# 3. Execution Flags — All False
# ===================================================================


class TestExecutionFlags:
    """All execution capability flags are false."""

    def test_implemented_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.execution.implemented is False

    def test_enabled_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.execution.enabled is False

    def test_provider_schema_sent_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.execution.provider_schema_sent is False

    def test_dispatch_available_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.execution.dispatch_available is False

    def test_audit_available_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.execution.audit_available is False


# ===================================================================
# 4. Safety Flags
# ===================================================================


class TestSafetyFlags:
    """Safety flags are read-only and correct."""

    def test_read_only_is_true(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.safety.read_only is True

    def test_side_effects_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.safety.side_effects is False

    def test_write_enabled_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.safety.write_enabled is False

    def test_execute_available_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.safety.execute_available is False

    def test_policy_mutation_available_is_false(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.safety.policy_mutation_available is False


# ===================================================================
# 5. Limits — From Static Module
# ===================================================================


class TestLimits:
    """Limits match static policy module constants."""

    def test_limits_match_static_module(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        limits = status.limits
        assert limits.max_argument_payload_bytes == MAX_ARGUMENT_PAYLOAD_BYTES
        assert limits.max_argument_nesting_depth == MAX_ARGUMENT_NESTING_DEPTH
        assert limits.max_argument_string_length == MAX_ARGUMENT_STRING_LENGTH
        assert limits.max_argument_array_length == MAX_ARGUMENT_ARRAY_LENGTH
        assert limits.default_r0_timeout_seconds == DEFAULT_R0_TIMEOUT_SECONDS
        assert limits.default_r1_timeout_seconds == DEFAULT_R1_TIMEOUT_SECONDS
        assert limits.max_tool_timeout_seconds == MAX_TOOL_TIMEOUT_SECONDS
        assert limits.max_tool_calls_per_run == MAX_TOOL_CALLS_PER_RUN
        assert limits.max_global_concurrency == MAX_GLOBAL_TOOL_CONCURRENCY
        assert limits.max_concurrency_per_run == MAX_TOOL_CONCURRENCY_PER_RUN
        assert limits.max_serialized_output_bytes == MAX_SERIALIZED_OUTPUT_BYTES
        assert limits.max_agent_visible_output_bytes == MAX_AGENT_VISIBLE_OUTPUT_BYTES
        assert limits.max_web_preview_output_bytes == MAX_WEB_PREVIEW_OUTPUT_BYTES


# ===================================================================
# 6. Catalog — Default Returns 71
# ===================================================================


class TestCatalogDefault:
    """Default catalog query returns all 71 tools."""

    def test_default_returns_71_total(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.total == 71

    def test_default_page_is_1(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.page == 1

    def test_default_page_size_is_25(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.page_size == 25

    def test_default_total_pages(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.total_pages == math.ceil(71 / 25)

    def test_default_items_count_matches_page_size(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert len(response.items) == 25

    def test_default_sort_is_name_ascending(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        names = [item.canonical_name for item in response.items]
        assert names == sorted(names)


# ===================================================================
# 7. Pagination
# ===================================================================


class TestPagination:
    """Pagination behavior."""

    def test_page_2_returns_correct_items(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page=2, page_size=25)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 25
        assert response.page == 2

    def test_last_page_returns_remainder(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page=3, page_size=25)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 71 - 50  # 21 remaining

    def test_page_beyond_total_returns_empty_items(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page=999, page_size=25)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 0
        assert response.total == 71  # Total still shows full count

    def test_page_size_1_returns_single_item(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=1)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 1
        assert response.total_pages == 71

    def test_page_size_100_returns_all(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 71
        assert response.total_pages == 1

    def test_total_pages_calculation(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=50)
        response = service.list_tool_catalog(query)
        assert response.total_pages == 2


# ===================================================================
# 8. Search (q parameter)
# ===================================================================


class TestSearch:
    """Search by canonicalName and rationalePreview."""

    def test_search_by_name_exact(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="terminal")
        response = service.list_tool_catalog(query)
        assert response.total == 1
        assert response.items[0].canonical_name == "terminal"

    def test_search_by_name_partial(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="browser")
        response = service.list_tool_catalog(query)
        assert response.total > 0
        for item in response.items:
            assert "browser" in item.canonical_name.lower()

    def test_search_by_rationale(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="Spotify")
        response = service.list_tool_catalog(query)
        # Should match spotify tools via rationale preview
        assert response.total >= 1

    def test_search_case_insensitive(self, service: DevToolPolicyQueryService) -> None:
        query_lower = validate_catalog_query(q="terminal")
        query_upper = validate_catalog_query(q="TERMINAL")
        resp_lower = service.list_tool_catalog(query_lower)
        resp_upper = service.list_tool_catalog(query_upper)
        assert resp_lower.total == resp_upper.total

    def test_search_no_match_returns_empty(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="zzz_nonexistent_tool_xyz")
        response = service.list_tool_catalog(query)
        assert response.total == 0
        assert len(response.items) == 0

    def test_search_empty_string_returns_all(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="")
        response = service.list_tool_catalog(query)
        # Empty string matches everything
        assert response.total == 71


# ===================================================================
# 9. Risk Filter
# ===================================================================


class TestRiskFilter:
    """Filter by risk level."""

    def test_filter_r0(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R0", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 1
        assert all(item.risk_rank == "R0" for item in response.items)

    def test_filter_r1(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R1", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 5
        assert all(item.risk_rank == "R1" for item in response.items)

    def test_filter_r2(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R2", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 19

    def test_filter_r3(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R3", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 26

    def test_filter_r4(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R4", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 17

    def test_filter_r5(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R5", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 3


# ===================================================================
# 10. Capability Filter
# ===================================================================


class TestCapabilityFilter:
    """Filter by capability tag."""

    def test_filter_pure_compute(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(capability="PURE_COMPUTE", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 1  # Only clarify
        assert response.items[0].canonical_name == "clarify"

    def test_filter_process_execution(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(capability="PROCESS_EXECUTION", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total >= 1
        for item in response.items:
            assert "PROCESS_EXECUTION" in item.capabilities

    def test_filter_scheduling(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(capability="SCHEDULING", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total >= 1
        for item in response.items:
            assert "SCHEDULING" in item.capabilities


# ===================================================================
# 11. Policy Status Filter
# ===================================================================


class TestPolicyStatusFilter:
    """Filter by derived policy status."""

    def test_filter_permanently_denied(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(policy_status="PERMANENTLY_DENIED", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 26
        assert all(item.policy_status == "PERMANENTLY_DENIED" for item in response.items)

    def test_filter_candidate(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(policy_status="CANDIDATE", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 6
        assert all(item.policy_status == "CANDIDATE" for item in response.items)

    def test_filter_unlisted(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(policy_status="UNLISTED", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 39
        assert all(item.policy_status == "UNLISTED" for item in response.items)

    def test_filter_statically_allowed_is_0(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(policy_status="STATICALLY_ALLOWED", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 0


# ===================================================================
# 12. Combined Filters
# ===================================================================


class TestCombinedFilters:
    """Multiple filters applied simultaneously."""

    def test_risk_and_capability_combined(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R4", capability="BROWSER_CONTROL", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total >= 1
        for item in response.items:
            assert item.risk_rank == "R4"
            assert "BROWSER_CONTROL" in item.capabilities

    def test_risk_and_policy_status_combined(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(risk="R0", policy_status="CANDIDATE", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 1  # clarify is R0 and CANDIDATE
        assert response.items[0].canonical_name == "clarify"

    def test_search_and_risk_combined(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="spotify", risk="R2", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total >= 1
        for item in response.items:
            assert "spotify" in item.canonical_name.lower()
            assert item.risk_rank == "R2"


# ===================================================================
# 13. Sort
# ===================================================================


class TestSort:
    """Sort behavior."""

    def test_sort_name_asc(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(sort="nameAsc", page_size=100)
        response = service.list_tool_catalog(query)
        names = [item.canonical_name for item in response.items]
        assert names == sorted(names)

    def test_sort_name_desc(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(sort="nameDesc", page_size=100)
        response = service.list_tool_catalog(query)
        names = [item.canonical_name for item in response.items]
        assert names == sorted(names, reverse=True)

    def test_sort_risk_asc(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(sort="riskAsc", page_size=100)
        response = service.list_tool_catalog(query)
        # First item should be R0 (lowest risk)
        assert response.items[0].risk_rank == "R0"
        # Last items should be R5
        assert response.items[-1].risk_rank == "R5"

    def test_sort_risk_desc(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(sort="riskDesc", page_size=100)
        response = service.list_tool_catalog(query)
        # First items should be R5 (highest risk)
        assert response.items[0].risk_rank == "R5"
        # Last item should be R0
        assert response.items[-1].risk_rank == "R0"


# ===================================================================
# 14. Empty Result
# ===================================================================


class TestEmptyResult:
    """Empty results return 200 with empty items."""

    def test_nonexistent_filter_returns_empty(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="zzz_no_match", page_size=100)
        response = service.list_tool_catalog(query)
        assert response.total == 0
        assert len(response.items) == 0
        assert response.total_pages == 1  # min(1, ceil(0/100))

    def test_page_beyond_returns_empty(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page=999)
        response = service.list_tool_catalog(query)
        assert len(response.items) == 0
        assert response.total == 71  # Total unchanged


# ===================================================================
# 15. Validation — Invalid q
# ===================================================================


class TestInvalidQuery:
    """Invalid query parameters raise errors."""

    def test_q_too_long_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(q="a" * 121)

    def test_q_at_max_length_ok(self) -> None:
        query = validate_catalog_query(q="a" * 120)
        assert query.q == "a" * 120

    def test_dangerous_param_execute_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"execute": "true"})

    def test_dangerous_param_force_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"force": "1"})

    def test_dangerous_param_enable_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"enable": "true"})

    def test_dangerous_param_write_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"write": "1"})

    def test_dangerous_param_dispatch_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"dispatch": "true"})

    def test_dangerous_param_override_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(extra_params={"override": "1"})


# ===================================================================
# 16. Validation — Invalid Risk
# ===================================================================


class TestInvalidRisk:
    """Invalid risk parameter raises InvalidToolRiskError."""

    def test_invalid_risk_raises_error(self) -> None:
        with pytest.raises(InvalidToolRiskError):
            validate_catalog_query(risk="R6")

    def test_lowercase_risk_raises_error(self) -> None:
        with pytest.raises(InvalidToolRiskError):
            validate_catalog_query(risk="r0")

    def test_empty_risk_raises_error(self) -> None:
        with pytest.raises(InvalidToolRiskError):
            validate_catalog_query(risk="")

    def test_valid_risks_ok(self) -> None:
        for risk in ("R0", "R1", "R2", "R3", "R4", "R5"):
            query = validate_catalog_query(risk=risk)
            assert query.risk is not None
            assert query.risk.value == risk


# ===================================================================
# 17. Validation — Invalid Capability
# ===================================================================


class TestInvalidCapability:
    """Invalid capability parameter raises InvalidToolCapabilityError."""

    def test_invalid_capability_raises_error(self) -> None:
        with pytest.raises(InvalidToolCapabilityError):
            validate_catalog_query(capability="INVALID_CAP")

    def test_lowercase_capability_raises_error(self) -> None:
        with pytest.raises(InvalidToolCapabilityError):
            validate_catalog_query(capability="pure_compute")


# ===================================================================
# 18. Validation — Invalid Policy Status
# ===================================================================


class TestInvalidPolicyStatus:
    """Invalid policy status parameter raises InvalidToolPolicyStatusError."""

    def test_invalid_status_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyStatusError):
            validate_catalog_query(policy_status="ENABLED")

    def test_lowercase_status_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyStatusError):
            validate_catalog_query(policy_status="candidate")


# ===================================================================
# 19. Validation — Invalid Sort
# ===================================================================


class TestInvalidSort:
    """Invalid sort parameter raises InvalidToolSortError."""

    def test_invalid_sort_raises_error(self) -> None:
        with pytest.raises(InvalidToolSortError):
            validate_catalog_query(sort="invalid")

    def test_lowercase_sort_raises_error(self) -> None:
        with pytest.raises(InvalidToolSortError):
            validate_catalog_query(sort="nameasc")


# ===================================================================
# 20. Validation — Invalid Page
# ===================================================================


class TestInvalidPage:
    """Invalid page parameter raises InvalidToolPolicyQueryError."""

    def test_page_zero_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(page=0)

    def test_negative_page_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(page=-1)


# ===================================================================
# 21. Validation — Invalid PageSize
# ===================================================================


class TestInvalidPageSize:
    """Invalid page_size parameter raises InvalidToolPolicyQueryError."""

    def test_page_size_zero_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(page_size=0)

    def test_page_size_over_100_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(page_size=101)

    def test_page_size_negative_raises_error(self) -> None:
        with pytest.raises(InvalidToolPolicyQueryError):
            validate_catalog_query(page_size=-1)

    def test_page_size_100_ok(self) -> None:
        query = validate_catalog_query(page_size=100)
        assert query.page_size == 100

    def test_page_size_1_ok(self) -> None:
        query = validate_catalog_query(page_size=1)
        assert query.page_size == 1


# ===================================================================
# 22. DTO Whitelist
# ===================================================================


class TestDTOWhitelist:
    """Catalog Item DTO only contains allowed fields."""

    ALLOWED_FIELDS = frozenset({
        "canonical_name",
        "primary_risk",
        "risk_rank",
        "capabilities",
        "permanently_denied",
        "candidate_allowlisted",
        "statically_allowed",
        "allowed",
        "policy_status",
        "reason_code",
        "source_module",
        "rationale_preview",
        "execution_available",
        "schema_preview_available",
        "dry_run_available",
    })

    FORBIDDEN_FIELDS = frozenset({
        "handler", "callable", "function", "absolute_path", "module_path",
        "registry_object", "tool_schema", "provider_schema", "api_key",
        "base_url", "authorization", "headers", "environment", "token",
        "password", "credentials", "traceback", "stack", "dispatch",
        "force", "override",
    })

    def test_catalog_item_has_only_allowed_fields(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            item_fields = {f.name for f in item.__dataclass_fields__.values()}
            assert item_fields == self.ALLOWED_FIELDS, (
                f"Unexpected fields: {item_fields - self.ALLOWED_FIELDS}"
            )

    def test_catalog_item_has_no_forbidden_fields(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            for field in self.FORBIDDEN_FIELDS:
                assert not hasattr(item, field), f"Forbidden field present: {field}"

    def test_policy_status_dto_fields(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        expected = {
            "mode", "inventory_count", "risk_counts",
            "permanent_denylist_count", "candidate_allowlist_count",
            "enabled_allowlist_count", "execution", "limits", "safety",
        }
        actual = {f.name for f in status.__dataclass_fields__.values()}
        assert actual == expected


# ===================================================================
# 23. No Absolute Paths
# ===================================================================


class TestNoAbsolutePaths:
    """DTOs must not contain absolute paths."""

    def test_no_absolute_paths_in_rationale(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert not item.rationale_preview.startswith("/"), (
                f"Absolute path in rationale for {item.canonical_name}"
            )
            assert "/Users/" not in item.rationale_preview
            assert "/home/" not in item.rationale_preview
            assert "file://" not in item.rationale_preview

    def test_no_absolute_paths_in_source_module(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert not item.source_module.startswith("/"), (
                f"Absolute path in source_module for {item.canonical_name}"
            )


# ===================================================================
# 24. No Secrets
# ===================================================================


class TestNoSecrets:
    """DTOs must not contain secrets."""

    SECRET_PATTERNS = ("api_key", "password", "secret", "token", "bearer")

    def test_no_secrets_in_rationale(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            for pattern in self.SECRET_PATTERNS:
                assert pattern not in item.rationale_preview.lower(), (
                    f"Secret pattern '{pattern}' in rationale for {item.canonical_name}"
                )


# ===================================================================
# 25. All allowed=false
# ===================================================================


class TestAllNotAllowed:
    """Every tool has allowed=False."""

    def test_all_tools_not_allowed(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert item.allowed is False, (
                f"{item.canonical_name} has allowed=True"
            )


# ===================================================================
# 26. All Unavailable Flags = False
# ===================================================================


class TestAllUnavailableFalse:
    """All execution-related availability flags are False."""

    def test_execution_available_false(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert item.execution_available is False

    def test_schema_preview_available_false(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert item.schema_preview_available is False

    def test_dry_run_available_false(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert item.dry_run_available is False


# ===================================================================
# 27. Policy Status Mode
# ===================================================================


class TestPolicyMode:
    """Mode is DEFAULT_DENY."""

    def test_mode_is_default_deny(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        assert status.mode == "DEFAULT_DENY"


# ===================================================================
# 28. Catalog Response Structure
# ===================================================================


class TestCatalogResponseStructure:
    """Catalog response has correct structure."""

    def test_catalog_has_summary(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        assert response.summary.inventory_count == 71
        assert response.summary.permanent_denylist_count == 26
        assert response.summary.candidate_allowlist_count == 6
        assert response.summary.enabled_allowlist_count == 0

    def test_catalog_has_safety(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.safety.read_only is True
        assert response.safety.side_effects is False
        assert response.safety.execute_available is False

    def test_catalog_has_filters(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="test", risk="R0", sort="nameDesc")
        response = service.list_tool_catalog(query)
        assert response.filters.q == "test"
        assert response.filters.risk == "R0"
        assert response.filters.sort == "nameDesc"

    def test_catalog_filters_null_defaults(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        assert response.filters.q is None
        assert response.filters.risk is None
        assert response.filters.capability is None
        assert response.filters.policy_status is None
        assert response.filters.sort == "nameAsc"


# ===================================================================
# 29. Error Model
# ===================================================================


class TestErrorModel:
    """Error types have correct codes and no sensitive data."""

    def test_invalid_query_error_code(self) -> None:
        err = InvalidToolPolicyQueryError("test")
        assert err.code == "INVALID_TOOL_POLICY_QUERY"
        assert "test" in err.message

    def test_invalid_risk_error_code(self) -> None:
        err = InvalidToolRiskError()
        assert err.code == "INVALID_TOOL_RISK"
        assert "R0" in err.message

    def test_invalid_capability_error_code(self) -> None:
        err = InvalidToolCapabilityError()
        assert err.code == "INVALID_TOOL_CAPABILITY"

    def test_invalid_policy_status_error_code(self) -> None:
        err = InvalidToolPolicyStatusError()
        assert err.code == "INVALID_TOOL_POLICY_STATUS"

    def test_invalid_sort_error_code(self) -> None:
        err = InvalidToolSortError()
        assert err.code == "INVALID_TOOL_SORT"

    def test_data_invalid_error_code(self) -> None:
        err = ToolPolicyDataInvalidError()
        assert err.code == "TOOL_POLICY_DATA_INVALID"

    def test_error_messages_no_absolute_paths(self) -> None:
        errors = [
            InvalidToolPolicyQueryError("test msg"),
            InvalidToolRiskError(),
            InvalidToolCapabilityError(),
            InvalidToolPolicyStatusError(),
            InvalidToolSortError(),
            ToolPolicyDataInvalidError(),
        ]
        for err in errors:
            assert "/Users/" not in err.message
            assert "/home/" not in err.message

    def test_error_messages_no_tracebacks(self) -> None:
        errors = [
            InvalidToolPolicyQueryError("test"),
            InvalidToolRiskError(),
            InvalidToolSortError(),
        ]
        for err in errors:
            assert "Traceback" not in err.message
            assert "stack" not in err.message.lower()

    def test_errors_inherit_from_base(self) -> None:
        assert issubclass(InvalidToolPolicyQueryError, ToolPolicyQueryError)
        assert issubclass(InvalidToolRiskError, ToolPolicyQueryError)
        assert issubclass(InvalidToolCapabilityError, ToolPolicyQueryError)
        assert issubclass(InvalidToolPolicyStatusError, ToolPolicyQueryError)
        assert issubclass(InvalidToolSortError, ToolPolicyQueryError)
        assert issubclass(ToolPolicyDataInvalidError, ToolPolicyQueryError)


# ===================================================================
# 30. No Registry Import
# ===================================================================


class TestNoRegistryImport:
    """Service does not import Registry."""

    def test_no_registry_import_in_source(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc

        source = Path(svc.__file__).read_text(encoding="utf-8")
        # Check import lines only (docstrings may mention these terms)
        import_lines = [
            line for line in source.splitlines()
            if line.strip().startswith(("import ", "from "))
        ]
        import_text = "\n".join(import_lines)
        assert "tools.registry" not in import_text
        assert "tools/registry" not in import_text
        assert "registry.dispatch" not in import_text
        assert "handle_function_call" not in import_text


# ===================================================================
# 31. No Handler Initialization
# ===================================================================


class TestNoHandlerInit:
    """Service does not initialize tool handlers."""

    def test_no_handler_imports(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc

        source = Path(svc.__file__).read_text(encoding="utf-8")
        assert "from tools" not in source or "from hermes_cli.dev_web_tool_policy" in source
        # Specifically no handler imports
        assert "import tools." not in source


# ===================================================================
# 32. No Provider / SessionDB / FastAPI / Agent
# ===================================================================


def _get_import_lines(module: object) -> str:
    """Extract only import/from lines from a module's source."""
    source = Path(module.__file__).read_text(encoding="utf-8")
    import_lines = [
        line for line in source.splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    return "\n".join(import_lines)


class TestNoUnsafeImports:
    """Service has no Provider, SessionDB, FastAPI, or Agent imports."""

    def test_no_provider_import(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "provider" not in import_text.lower()

    def test_no_sessiondb_import(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "SessionDB" not in import_text
        assert "session_db" not in import_text
        assert "hermes_state" not in import_text

    def test_no_fastapi_import(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "fastapi" not in import_text.lower()

    def test_no_agent_import(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "run_agent" not in import_text


# ===================================================================
# 33. No Filesystem / Database / Network Access
# ===================================================================


class TestNoIOAccess:
    """Service source has no filesystem, database, or network access."""

    def test_no_filesystem_imports(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "import os" not in import_text
        assert "from pathlib" not in import_text
        assert "import shutil" not in import_text

    def test_no_database_imports(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "import sqlite3" not in import_text
        assert "aiosqlite" not in import_text

    def test_no_network_imports(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc
        import_text = _get_import_lines(svc)
        assert "import urllib" not in import_text
        assert "import httpx" not in import_text
        assert "import requests" not in import_text
        assert "import aiohttp" not in import_text


# ===================================================================
# 34. No Thread / Cache / Lock / Mutable State
# ===================================================================


class TestNoMutableState:
    """Service has no threads, caches, locks, or mutable global state."""

    def test_no_threading(self) -> None:
        import hermes_cli.dev_web_tool_policy_service as svc

        source = Path(svc.__file__).read_text(encoding="utf-8")
        assert "import threading" not in source
        assert "from threading" not in source
        assert "import subprocess" not in source

    def test_service_creates_no_global_mutable_state(self) -> None:
        """Service instances are independent and stateless."""
        s1 = DevToolPolicyQueryService()
        s2 = DevToolPolicyQueryService()
        r1 = s1.get_policy_status()
        r2 = s2.get_policy_status()
        assert r1.inventory_count == r2.inventory_count
        assert r1.mode == r2.mode


# ===================================================================
# 35. Does Not Modify Static Policy
# ===================================================================


class TestDoesNotModifyStaticPolicy:
    """Service reads but never modifies the static policy module."""

    def test_static_allowlist_still_empty(self, service: DevToolPolicyQueryService) -> None:
        service.get_policy_status()
        assert len(STATIC_ALLOWLIST) == 0

    def test_static_denylist_unchanged(self, service: DevToolPolicyQueryService) -> None:
        service.get_policy_status()
        assert len(STATIC_DENYLIST) == 26

    def test_inventory_unchanged(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        service.list_tool_catalog(query)
        assert len(TOOL_POLICY_INVENTORY) == 71


# ===================================================================
# 36. Import Zero Side Effects
# ===================================================================


class TestImportZeroSideEffects:
    """Importing the service module has no side effects."""

    def test_import_has_no_filesystem_side_effects(self, tmp_path: Path) -> None:
        hermes_home = tmp_path / "hermes-home"
        script = textwrap.dedent(f"""\
            import sys
            sys.argv = ["test"]
            from hermes_cli.dev_web_tool_policy_service import DevToolPolicyQueryService
            import os
            home = "{hermes_home}"
            if os.path.exists(home):
                for root, dirs, files in os.walk(home):
                    for f in files:
                        full = os.path.join(root, f)
                        print(f"FILE: {{full}}")
            print("OK")
        """)
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(tmp_path),
                "HERMES_HOME": str(hermes_home),
                "VIRTUAL_ENV": "",
                **{
                    k: v
                    for k, v in __import__("os").environ.items()
                    if k.startswith("PYTHON")
                },
            },
            timeout=30,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "OK" in result.stdout
        tool_related = [
            line for line in result.stdout.splitlines()
            if line.startswith("FILE:") and (
                "tool" in line.lower() or "audit" in line.lower()
            )
        ]
        assert not tool_related, f"Unexpected tool-related files: {tool_related}"


# ===================================================================
# 37. Rationale Preview Truncation
# ===================================================================


class TestRationaleTruncation:
    """Rationale preview is truncated and redacted."""

    def test_rationale_max_200_chars(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert len(item.rationale_preview) <= 200, (
                f"{item.canonical_name} rationale > 200: {len(item.rationale_preview)}"
            )

    def test_rationale_no_newlines(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            assert "\n" not in item.rationale_preview
            assert "\r" not in item.rationale_preview


# ===================================================================
# 38. Redaction Functions
# ===================================================================


class TestRedaction:
    """Path and secret redaction."""

    def test_redact_macos_path(self) -> None:
        assert _redact_paths_and_secrets("/Users/test/file.txt") == "[local-path]"

    def test_redact_linux_path(self) -> None:
        assert _redact_paths_and_secrets("/home/user/file.txt") == "[local-path]"

    def test_redact_file_uri(self) -> None:
        assert _redact_paths_and_secrets("file:///Users/test/file") == "[file-uri-redacted]"

    def test_redact_api_key(self) -> None:
        result = _redact_paths_and_secrets("api_key=sk-12345")
        assert "sk-12345" not in result
        assert "[secret-redacted]" in result

    def test_truncate_rationale(self) -> None:
        long_text = "a" * 300
        result = _truncate_rationale(long_text)
        assert len(result) <= 200

    def test_truncate_empty_string(self) -> None:
        assert _truncate_rationale("") == ""


# ===================================================================
# 39. Policy Status Derivation
# ===================================================================


class TestPolicyStatusDerivation:
    """Policy status derivation logic."""

    def test_denied_tools_get_permanently_denied(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="terminal")
        response = service.list_tool_catalog(query)
        assert response.items[0].policy_status == "PERMANENTLY_DENIED"

    def test_candidate_tools_get_candidate(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="clarify")
        response = service.list_tool_catalog(query)
        assert response.items[0].policy_status == "CANDIDATE"

    def test_other_tools_get_unlisted(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="web_search")
        response = service.list_tool_catalog(query)
        assert response.items[0].policy_status == "UNLISTED"

    def test_status_counts_sum_to_71(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        denied = sum(1 for i in response.items if i.policy_status == "PERMANENTLY_DENIED")
        candidate = sum(1 for i in response.items if i.policy_status == "CANDIDATE")
        unlisted = sum(1 for i in response.items if i.policy_status == "UNLISTED")
        statically = sum(1 for i in response.items if i.policy_status == "STATICALLY_ALLOWED")
        assert denied == 26
        assert candidate == 6
        assert unlisted == 39
        assert statically == 0
        assert denied + candidate + unlisted + statically == 71


# ===================================================================
# 40. Capabilities Format
# ===================================================================


class TestCapabilitiesFormat:
    """Capabilities are sorted string tuples."""

    def test_capabilities_are_sorted(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(q="terminal")
        response = service.list_tool_catalog(query)
        item = response.items[0]
        assert item.capabilities == tuple(sorted(item.capabilities))

    def test_capabilities_are_strings(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=100)
        response = service.list_tool_catalog(query)
        for item in response.items:
            for cap in item.capabilities:
                assert isinstance(cap, str)


# ===================================================================
# 41. DTO Frozen / Immutable
# ===================================================================


class TestDTOsFrozen:
    """DTOs are frozen (immutable)."""

    def test_catalog_item_is_frozen(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query(page_size=1)
        response = service.list_tool_catalog(query)
        item = response.items[0]
        with pytest.raises(AttributeError):
            item.allowed = True  # type: ignore[misc]

    def test_policy_status_dto_is_frozen(self, service: DevToolPolicyQueryService) -> None:
        status = service.get_policy_status()
        with pytest.raises(AttributeError):
            status.mode = "ALL_ALLOWED"  # type: ignore[misc]

    def test_response_dto_is_frozen(self, service: DevToolPolicyQueryService) -> None:
        query = validate_catalog_query()
        response = service.list_tool_catalog(query)
        with pytest.raises(AttributeError):
            response.total = 0  # type: ignore[misc]
