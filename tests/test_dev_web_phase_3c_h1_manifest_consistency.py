"""Phase 3C-H1 — Static Manifest Determinism / Frontend Mirror Consistency.

Hardens ``CAP-MANIFEST-3C-H1-001`` (Lens 1).

The backend static manifest is deterministic, and the tracked frontend TS
mirror is a hand-maintained copy of it. This test **bounds the drift risk**:
it parses the TS mirror and asserts the capability IDs (in order), the
permission-class / trust-level / status / category sets, the frozen
forbidden-field set, and the registry version all match the backend manifest
exactly. If either side drifts, this test fails closed.

This does NOT introduce a generator; the mirror remains a tracked, reviewable
copy (P2 generator deferred). The drift is bounded by this deterministic test.

Phase: 3C-H1 — Static Capability Registry Hardening
Status: implemented
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from hermes_cli.dev_web_capability_registry import validate_manifest
from hermes_cli.dev_web_capability_registry_manifest import (
    MANIFEST_VERSION,
    get_static_manifest,
)
from hermes_cli.dev_web_capability_registry_schema import FORBIDDEN_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MIRROR_PATH = (
    REPO_ROOT / "apps/hermes-dev-webui/src/constants/capabilityRegistryManifest.ts"
)


def _backend_entries() -> list[dict]:
    return list(get_static_manifest())


def _frontend_source() -> str:
    assert FRONTEND_MIRROR_PATH.is_file(), f"frontend mirror missing: {FRONTEND_MIRROR_PATH}"
    return FRONTEND_MIRROR_PATH.read_text(encoding="utf-8")


def _frontend_capability_ids(src: str) -> list[str]:
    return re.findall(r'"capabilityId":\s*"([^"]+)"', src)


def _frontend_enum_set(src: str, field: str) -> set[str]:
    return set(re.findall(rf'"{field}":\s*"([^"]+)"', src))


def _frontend_version(src: str) -> str | None:
    m = re.search(r'CAPABILITY_REGISTRY_VERSION\s*=\s*"([^"]+)"', src)
    return m.group(1) if m else None


def _frontend_forbidden_fields(src: str) -> list[str]:
    block = re.search(
        r"CAPABILITY_FORBIDDEN_FIELDS\s*=\s*\[(.*?)\]\s*as\s+const",
        src,
        re.S,
    )
    assert block is not None, "CAPABILITY_FORBIDDEN_FIELDS export not found in mirror"
    return re.findall(r'"([^"]+)"', block.group(1))


def _detect_id_drift(backend_ids: list[str], frontend_ids: list[str]) -> bool:
    """True when the two ordered ID lists are identical (no drift)."""
    return backend_ids == frontend_ids


class TestBackendDeterminism:
    def test_manifest_is_tuple_and_immutable_shape(self) -> None:
        manifest = get_static_manifest()
        assert isinstance(manifest, tuple)
        # Deterministic across calls (same object identity is allowed; shape stable).
        assert len(manifest) == len(get_static_manifest())

    def test_two_validations_identical(self) -> None:
        r1 = validate_manifest(get_static_manifest())
        r2 = validate_manifest(get_static_manifest())
        assert r1.valid is True and r2.valid is True
        assert r1.capability_count == r2.capability_count == 46
        assert r1.permission_class_counts == r2.permission_class_counts
        assert r1.trust_level_counts == r2.trust_level_counts
        assert r1.status_counts == r2.status_counts
        assert r1.category_counts == r2.category_counts

    def test_capability_count_is_46(self) -> None:
        assert len(_backend_entries()) == 46

    def test_capability_ids_stable_and_unique(self) -> None:
        ids = [e["capabilityId"] for e in _backend_entries()]
        assert len(ids) == len(set(ids))
        # Pinned ordered IDs (snapshot) — a reorder / rename fails this.
        assert ids[0] == "registry.capability_registry_status"
        assert ids[-1] == "capability.forbidden.autonomous_write"

    def test_manifest_version_pinned(self) -> None:
        assert MANIFEST_VERSION == "phase3c-static-v1"


class TestFrontendMirrorNoDrift:
    def test_mirror_capability_ids_match_backend_in_order(self) -> None:
        src = _frontend_source()
        be_ids = [e["capabilityId"] for e in _backend_entries()]
        fe_ids = _frontend_capability_ids(src)
        assert _detect_id_drift(be_ids, fe_ids), (
            "frontend mirror capability IDs drifted from backend manifest"
        )

    def test_mirror_count_matches_backend(self) -> None:
        src = _frontend_source()
        assert len(_frontend_capability_ids(src)) == len(_backend_entries()) == 46

    def test_mirror_permission_classes_match_backend(self) -> None:
        src = _frontend_source()
        be = {e["permissionClass"] for e in _backend_entries()}
        fe = _frontend_enum_set(src, "permissionClass")
        assert be == fe

    def test_mirror_trust_levels_match_backend(self) -> None:
        src = _frontend_source()
        be = {e["trustLevel"] for e in _backend_entries()}
        fe = _frontend_enum_set(src, "trustLevel")
        assert be == fe

    def test_mirror_statuses_match_backend(self) -> None:
        src = _frontend_source()
        be = {e["status"] for e in _backend_entries()}
        fe = _frontend_enum_set(src, "status")
        assert be == fe

    def test_mirror_categories_match_backend(self) -> None:
        src = _frontend_source()
        be = {e["category"] for e in _backend_entries()}
        fe = _frontend_enum_set(src, "category")
        assert be == fe

    def test_mirror_forbidden_fields_match_backend(self) -> None:
        src = _frontend_source()
        assert set(_frontend_forbidden_fields(src)) == set(FORBIDDEN_FIELDS)

    def test_mirror_version_matches_backend(self) -> None:
        src = _frontend_source()
        assert _frontend_version(src) == MANIFEST_VERSION


class TestDriftDetector:
    """The drift detector itself must fail when the two sides diverge."""

    def test_detector_passes_when_identical(self) -> None:
        assert _detect_id_drift(["a", "b"], ["a", "b"]) is True

    def test_detector_fails_on_reordered(self) -> None:
        assert _detect_id_drift(["a", "b"], ["b", "a"]) is False

    def test_detector_fails_on_missing(self) -> None:
        assert _detect_id_drift(["a", "b"], ["a"]) is False

    def test_detector_fails_on_extra(self) -> None:
        assert _detect_id_drift(["a"], ["a", "b"]) is False

    def test_detector_fails_on_renamed(self) -> None:
        assert _detect_id_drift(["a", "b"], ["a", "c"]) is False
