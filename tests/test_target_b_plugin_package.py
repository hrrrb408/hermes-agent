"""Phase 4B — Target B Signed Plugin Package schema layer tests.

Asserts ``hermes_cli/dev_web_target_b_package.py`` is inert, frozen, and
fail-closed:

  - the package validators validate SHAPE + FORMAT only — they never load,
    import, unpack, execute, fetch, or trust a package;
  - a perfectly-shaped package is ``valid`` but NOT ``trusted`` / ``loadable``
    / ``executable``;
  - malformed id / version / publisher / manifest / permission / capability /
    entrypoint / checksum / signature metadata is rejected;
  - the example descriptor is fake / not loaded / not executable and uses a
    ``.invalid`` registry source;
  - the module source contains NO filesystem / network / subprocess /
    dynamic-import / eval / exec primitive, and no production home or production
    ``state.db`` access.

Boundary: this test never touches ``~/.hermes``, never opens production
``state.db``, never starts a gateway / dashboard, and introduces no new route.
All forbidden-path assertions use fake / string-policy paths only.

Phase: 4B — Target B End-to-End Implementation (gated)
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hermes_cli import dev_web_target_b_package as package
from hermes_cli.dev_web_target_b_package import (
    PACKAGE_PERMISSION_TAXONOMY,
    PACKAGE_CAPABILITY_TAXONOMY,
    assert_package_layer_disabled,
    build_example_package_descriptor,
    validate_plugin_package_capabilities,
    validate_plugin_package_checksum_metadata,
    validate_plugin_package_entrypoints,
    validate_plugin_package_identity,
    validate_plugin_package_permissions,
    validate_plugin_package_shape,
    validate_plugin_package_signature_metadata,
    validate_plugin_package_without_loading,
)


def _valid_raw_descriptor() -> dict:
    return {
        "package_id": "example.plugin.alpha",
        "package_name": "Example Plugin Alpha",
        "version": "0.1.0",
        "publisher": "example.publisher",
        "manifest_version": "1.0",
        "hermes_min_version": "0.0.0",
        "descriptor": "descriptor-only",
        "capabilities": ["display.surface", "read.capability"],
        "permissions": ["filesystem.read"],
        "entrypoints": ["tool:example.tool.alpha"],
        "checksum": "sha256:" + "0" * 64,
        "signature": "fixture-hmac-sha256:" + "A" * 64,
        "signature_algorithm": "fixture-hmac-sha256",
        "registry_source": "https://registry.example.invalid",
        "sandbox_profile": "preview",
        "created_at": "1970-01-01T00:00:00Z",
        "review_metadata": ["preview"],
    }


class TestPackageShapeValidation:
    def test_valid_shape_present(self) -> None:
        shape_ok, missing = validate_plugin_package_shape(_valid_raw_descriptor())
        assert shape_ok is True
        assert missing == ()

    def test_missing_fields_reported_without_loading(self) -> None:
        shape_ok, missing = validate_plugin_package_shape({"package_id": "x"})
        assert shape_ok is False
        assert "version" in missing
        assert "signature" in missing

    def test_non_mapping_rejected(self) -> None:
        for bad in ("not-a-mapping", 42, None, ["a"]):
            shape_ok, _missing = validate_plugin_package_shape(bad)
            assert shape_ok is False


class TestPackageFormatValidation:
    def test_valid_identity(self) -> None:
        ok, reasons = validate_plugin_package_identity(_valid_raw_descriptor())
        assert ok is True
        assert reasons == ()

    def test_malformed_package_id_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["package_id"] = "Bad ID With Spaces!"
        ok, reasons = validate_plugin_package_identity(d)
        assert ok is False
        assert "package_id_malformed" in reasons

    def test_malformed_version_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["version"] = "not-a-version"
        ok, reasons = validate_plugin_package_identity(d)
        assert ok is False
        assert "version_malformed" in reasons

    def test_unknown_manifest_version_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["manifest_version"] = "99"
        ok, reasons = validate_plugin_package_identity(d)
        assert ok is False
        assert "manifest_version_unknown" in reasons

    def test_permissions_outside_taxonomy_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["permissions"] = ["filesystem.read", "shell.execute"]
        ok, reasons = validate_plugin_package_permissions(d)
        assert ok is False
        assert any("shell.execute" in r for r in reasons)

    def test_permissions_not_a_list_rejected(self) -> None:
        ok, reasons = validate_plugin_package_permissions({"permissions": "filesystem.read"})
        assert ok is False
        assert "permissions_not_a_string_list" in reasons

    def test_capability_implies_side_effect_rejected(self) -> None:
        d = _valid_raw_descriptor()
        # 'network.fetch' style capability is not in the taxonomy at all.
        d["capabilities"] = ["display.surface", "execute.code"]
        ok, reasons = validate_plugin_package_capabilities(d)
        assert ok is False

    def test_malformed_entrypoint_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["entrypoints"] = ["tool:ok", "import:os.sys"]
        ok, reasons = validate_plugin_package_entrypoints(d)
        assert ok is False

    def test_malformed_checksum_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["checksum"] = "not-a-checksum"
        ok, reasons = validate_plugin_package_checksum_metadata(d)
        assert ok is False

    def test_unknown_checksum_algorithm_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["checksum"] = "md5:" + "0" * 32
        ok, _reasons = validate_plugin_package_checksum_metadata(d)
        assert ok is False

    def test_malformed_signature_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["signature"] = "short"
        ok, reasons = validate_plugin_package_signature_metadata(d)
        assert ok is False
        assert "signature_malformed" in reasons

    def test_unknown_signature_algorithm_rejected(self) -> None:
        d = _valid_raw_descriptor()
        d["signature_algorithm"] = "rot13"
        ok, reasons = validate_plugin_package_signature_metadata(d)
        assert ok is False
        assert "signature_algorithm_unknown" in reasons


class TestAggregateValidation:
    def test_valid_package_is_not_trusted_or_loadable_or_executable(self) -> None:
        result = validate_plugin_package_without_loading(_valid_raw_descriptor())
        assert result.valid is True
        assert result.trusted is False
        assert result.loadable is False
        assert result.executable is False

    def test_invalid_package_is_not_valid_and_not_trusted(self) -> None:
        result = validate_plugin_package_without_loading({"package_id": "Bad"})
        assert result.valid is False
        assert result.trusted is False
        assert result.loadable is False
        assert result.executable is False

    def test_non_mapping_aggregate(self) -> None:
        for bad in ("x", 42, None):
            result = validate_plugin_package_without_loading(bad)
            assert result.valid is False
            assert result.trusted is False


class TestExampleDescriptorAndBoundary:
    def test_example_descriptor_is_fake_not_loaded_not_executable(self) -> None:
        ex = build_example_package_descriptor()
        assert ex.example_only is True
        assert ex.not_loaded is True
        assert ex.not_executable is True
        assert ex.registry_source == "https://registry.example.invalid"

    def test_example_raw_descriptor_validates_shape_only(self) -> None:
        ex = build_example_package_descriptor()
        result = validate_plugin_package_without_loading(ex.to_raw_descriptor())
        assert result.valid is True
        assert result.trusted is False

    def test_taxonomy_sizes(self) -> None:
        assert len(PACKAGE_PERMISSION_TAXONOMY) == 15
        assert len(PACKAGE_CAPABILITY_TAXONOMY) == 6

    def test_assert_package_layer_disabled_passes(self) -> None:
        assert_package_layer_disabled()

    def test_no_positive_authorization_marker_in_projection(self) -> None:
        ex = build_example_package_descriptor()
        text = str(ex.to_safe_dict()).lower()
        for marker in (
            "production_runtime_go=true",
            "target_b_authorized=true",
            "implementation_authorization=go",
            "begin private key",
        ):
            assert marker not in text


class TestSourcePurity:
    MODULE_PATH = Path(package.__file__)

    FORBIDDEN_USAGE_PATTERNS = (
        "import subprocess",
        "subprocess.",
        "import importlib",
        "importlib.",
        "__import__",
        "import socket",
        "socket.",
        "requests.",
        "httpx.",
        "aiohttp.",
        "urllib",
        "eval(",
        "exec(",
        "os.system",
        "os.popen",
        "Path(",
        "Path.home",
        ".resolve(",
        "open(",
        "read_text(",
        "write_text(",
        "shutil.",
    )

    FORBIDDEN_PATH_STEMS = (
        "~/.hermes",
        ".hermes/state.db",
        "production/state.db",
        "state.db",
    )

    def test_module_source_contains_no_forbidden_usage_primitive(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8")
        for pattern in self.FORBIDDEN_USAGE_PATTERNS:
            assert pattern not in source, f"package source must not use {pattern!r}"

    def test_module_source_does_not_reference_production_home_or_state_db(self) -> None:
        source = self.MODULE_PATH.read_text(encoding="utf-8").lower()
        for stem in self.FORBIDDEN_PATH_STEMS:
            assert stem.lower() not in source, f"package source must not reference {stem!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
