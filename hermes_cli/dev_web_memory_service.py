"""Dev Web API memory query service.

Read-only service that queries memory data from the development HERMES_HOME
using the memory_router read-only functions. All queries are side-effect-free.

Importing this module has no side effects.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from hermes_cli.memory_router import (
    RootCategory,
    MemoryItem,
    ScoredCategory,
    ScoredMemory,
    active_root_categories,
    get_memory_system_summary,
    list_items,
    memory_dir,
    memory_root,
    parse_index,
    parse_root,
    score_category,
    score_memory_item,
    resolve_memory_uri,
    _truncate_text,
    _importance_rank,
    _query_terms,
    _contains,
    _priority_bonus,
    MEMORY_ID_RE,
)


# ── Path redaction ──

# Patterns for local absolute paths that must never appear in API responses.
# These patterns are intentionally broad to cover different user names and
# distributions, not just the current developer's machine.

# /Users/<segment>/... — macOS home directories
_RE_MACOS_PATH = re.compile(r"/Users/[^\s\"'`\)\]]+")

# /home/<segment>/... — Linux home directories
_RE_LINUX_PATH = re.compile(r"/home/[^\s\"'`\)\]]+")

# file:// URIs (with or without host)
_RE_FILE_URI = re.compile(r"file://[^\s\"'`\)\]]+")

# C:\... or D:\... — Windows absolute paths (defensive)
_RE_WINDOWS_PATH = re.compile(r"[A-Z]:\\[^\s\"'`\)\]]+", re.IGNORECASE)


def redact_local_paths(text: str) -> str:
    """Redact local file paths and file:// URIs from text.

    Replaces local absolute paths with ``[local-path]`` and ``file://``
    URIs with ``[file-uri-redacted]``. Preserves ``memory://`` references
    and ``http(s)://`` URLs.

    This function is applied to ``recordPreview`` and any other
    panel-facing text before it enters the DTO layer.
    """
    if not text:
        return text

    # Redact file:// URIs first (before path patterns match the /... part)
    text = _RE_FILE_URI.sub("[file-uri-redacted]", text)

    # Redact macOS and Linux absolute paths
    text = _RE_MACOS_PATH.sub("[local-path]", text)
    text = _RE_LINUX_PATH.sub("[local-path]", text)

    # Redact Windows absolute paths
    text = _RE_WINDOWS_PATH.sub("[local-path]", text)

    return text


# ── Custom exceptions ──


class MemoryUnavailableError(Exception):
    """Raised when the memory system is not available."""


class MemoryNotFoundError(Exception):
    """Raised when a requested memory item does not exist."""


class InvalidMemoryIdError(Exception):
    """Raised when a memory ID is malformed."""


# ── Constants ──

# Maximum memory ID length for API input validation
_MAX_MEMORY_ID_LENGTH = 128

# Maximum record preview characters
_MAX_RECORD_PREVIEW_CHARS = 5000

# Maximum query length for context preview
_MAX_QUERY_LENGTH = 1000

# Maximum categories in context preview
_MAX_CATEGORIES_LIMIT = 10

# Maximum memories in context preview
_MAX_MEMORIES_LIMIT = 20

# Maximum record chars in context preview
_MAX_RECORD_CHARS_LIMIT = 10000

# Safe category fields for DTO
_SAFE_CATEGORY_FIELDS = frozenset({
    "scope", "priority", "status", "keywords", "description",
})

# Safe item fields for DTO
_SAFE_ITEM_FIELDS = frozenset({
    "type", "importance", "ttl", "status", "tags",
    "created_at", "updated_at", "summary",
})


# ── DTO transformers (explicit whitelist) ──


def _transform_category_dto(
    name: str,
    category: RootCategory,
    *,
    include_count: bool = False,
    home: Path | None = None,
) -> dict[str, Any]:
    """Transform a RootCategory into a safe category DTO.

    Only whitelisted fields are included. No file paths or storage URIs.
    """
    fields = category.fields
    dto: dict[str, Any] = {
        "key": name,
        "title": name.replace("-", " ").replace("_", " ").title(),
        "description": fields.get("description", ""),
        "priority": fields.get("priority", ""),
        "keywords": fields.get("keywords", ""),
        "status": fields.get("status", "active"),
    }

    if include_count and home is not None:
        try:
            items = parse_index(name, home)
            active_count = sum(
                1 for item in items
                if item.fields.get("status", "active") == "active"
            )
            dto["memoryCount"] = len(items)
            dto["activeMemoryCount"] = active_count
        except Exception:
            dto["memoryCount"] = 0
            dto["activeMemoryCount"] = 0

    return dto


def _transform_item_list_dto(item: MemoryItem) -> dict[str, Any]:
    """Transform a MemoryItem into a safe list-item DTO.

    Only whitelisted fields are included. No storage URI or file paths.
    """
    fields = item.fields
    return {
        "id": item.memory_id,
        "category": item.category,
        "title": item.title,
        "summary": fields.get("summary", ""),
        "tags": fields.get("tags", ""),
        "type": fields.get("type", ""),
        "importance": fields.get("importance", ""),
        "status": fields.get("status", "active"),
        "updatedAt": fields.get("updated_at", ""),
    }


def _transform_item_detail_dto(
    item: MemoryItem,
    *,
    record_preview: str | None = None,
    truncated: bool = False,
) -> dict[str, Any]:
    """Transform a MemoryItem into a safe detail DTO.

    Only whitelisted fields are included. No storage URI or file paths.
    """
    fields = item.fields
    dto: dict[str, Any] = {
        "id": item.memory_id,
        "category": item.category,
        "title": item.title,
        "summary": fields.get("summary", ""),
        "tags": fields.get("tags", ""),
        "type": fields.get("type", ""),
        "importance": fields.get("importance", ""),
        "status": fields.get("status", "active"),
        "createdAt": fields.get("created_at", ""),
        "updatedAt": fields.get("updated_at", ""),
        "truncated": truncated,
    }
    if record_preview is not None:
        dto["recordPreview"] = record_preview
    return dto


def _transform_scored_category_dto(entry: ScoredCategory) -> dict[str, Any]:
    """Transform a ScoredCategory into a safe DTO."""
    return {
        "key": entry.category.name,
        "title": entry.category.name.replace("-", " ").replace("_", " ").title(),
        "score": entry.score,
        "priority": entry.category.fields.get("priority", ""),
    }


def _transform_scored_memory_dto(entry: ScoredMemory) -> dict[str, Any]:
    """Transform a ScoredMemory into a safe DTO."""
    item = entry.item
    return {
        "id": item.memory_id,
        "category": item.category,
        "title": item.title,
        "summary": item.fields.get("summary", ""),
        "score": entry.score,
        "truncated": entry.truncated,
    }


# ── Memory query service ──


class DevMemoryQueryService:
    """Read-only memory query service for the Dev Web API.

    All operations use the memory_router read-only functions with
    explicit home parameter. No writes, no LLM calls.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._home = hermes_home

    def is_available(self) -> bool:
        """Check whether the memory system is available."""
        root = memory_root(self._home)
        return root.exists() and root.is_file()

    # ── Status ──

    def get_status(self) -> dict[str, Any]:
        """Get memory system status.

        Returns a DTO dict with availability, counts, and capabilities.
        Never returns file paths.
        """
        if not self.is_available():
            return {
                "available": False,
                "readOnly": True,
                "rootCategories": {"total": 0, "active": 0, "archived": 0},
                "memories": {"total": 0, "active": 0, "archived": 0},
                "capabilities": {
                    "contextLoader": True,
                    "runtimeInjection": True,
                    "writer": True,
                    "reviewQueue": True,
                },
                "exposedCapabilities": {
                    "read": True,
                    "write": False,
                    "review": False,
                },
            }

        try:
            summary = get_memory_system_summary(self._home)
        except Exception:
            return {
                "available": False,
                "readOnly": True,
                "rootCategories": {"total": 0, "active": 0, "archived": 0},
                "memories": {"total": 0, "active": 0, "archived": 0},
                "capabilities": {
                    "contextLoader": True,
                    "runtimeInjection": True,
                    "writer": True,
                    "reviewQueue": True,
                },
                "exposedCapabilities": {
                    "read": True,
                    "write": False,
                    "review": False,
                },
            }

        categories_info = summary.get("categories", {})
        items_info = summary.get("memory_items", {})

        return {
            "available": True,
            "readOnly": True,
            "rootCategories": {
                "total": categories_info.get("total", 0),
                "active": categories_info.get("active", 0),
                "archived": categories_info.get("archived", 0),
            },
            "memories": {
                "total": items_info.get("total", 0),
                "active": items_info.get("active", 0),
                "archived": items_info.get("archived", 0),
            },
            "capabilities": {
                "contextLoader": True,
                "runtimeInjection": True,
                "writer": True,
                "reviewQueue": True,
            },
            "exposedCapabilities": {
                "read": True,
                "write": False,
                "review": False,
            },
        }

    # ── Categories ──

    def list_categories(
        self,
        *,
        include_archived: bool = False,
    ) -> list[dict[str, Any]]:
        """List memory categories.

        Returns a list of category DTOs. Never returns file paths.
        """
        if not self.is_available():
            raise MemoryUnavailableError()

        try:
            categories = active_root_categories(
                self._home,
                include_all=include_archived,
            )
        except Exception:
            raise MemoryUnavailableError()

        return [
            _transform_category_dto(
                name, cat,
                include_count=True,
                home=self._home,
            )
            for name, cat in categories.items()
        ]

    # ── Items ──

    def list_items(
        self,
        *,
        category: str | None = None,
        query: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List memory items with optional filtering.

        Returns a dict with 'items' (list of DTOs) and 'page' (pagination).
        Never returns storage URIs or file paths.
        """
        if not self.is_available():
            raise MemoryUnavailableError()

        try:
            all_items = list_items(
                self._home,
                include_all=include_archived,
            )
        except Exception:
            raise MemoryUnavailableError()

        # Filter by category
        if category:
            all_items = [
                item for item in all_items
                if item.category == category
            ]

        # Filter by query
        if query and query.strip():
            terms = _query_terms(query.strip())
            scored: list[tuple[MemoryItem, int]] = []
            for item in all_items:
                score = score_memory_item(query.strip(), item)
                if score > 0:
                    scored.append((item, score))
            scored.sort(key=lambda pair: (
                -pair[1],
                _importance_rank(pair[0].fields.get("importance", "")),
                pair[0].memory_id,
            ))
            all_items = [item for item, _score in scored]

        total = len(all_items)
        page_items = all_items[offset:offset + limit]

        return {
            "items": [_transform_item_list_dto(item) for item in page_items],
            "page": {
                "offset": offset,
                "limit": limit,
                "total": total,
                "hasMore": (offset + limit) < total,
            },
        }

    # ── Item detail ──

    def get_item(self, memory_id: str) -> dict[str, Any]:
        """Get a single memory item's detail by ID.

        Returns a detail DTO with optional record preview.
        Never returns storage URIs or file paths.
        """
        if not self.is_available():
            raise MemoryUnavailableError()

        location = list_items(self._home, include_all=True)
        target_item: MemoryItem | None = None
        for item in location:
            if item.memory_id == memory_id:
                target_item = item
                break

        if target_item is None:
            raise MemoryNotFoundError()

        # Try to load record preview
        record_preview: str | None = None
        truncated = False
        storage = target_item.storage
        if storage:
            try:
                record_path = resolve_memory_uri(storage, self._home)
                if record_path.exists():
                    text = record_path.read_text(encoding="utf-8")
                    text = redact_local_paths(text)
                    record_preview, truncated = _truncate_text(
                        text, _MAX_RECORD_PREVIEW_CHARS
                    )
            except (ValueError, OSError):
                # Invalid URI or read error — skip preview
                pass

        return _transform_item_detail_dto(
            target_item,
            record_preview=record_preview,
            truncated=truncated,
        )

    # ── Context preview ──

    def preview_context(
        self,
        query: str,
        *,
        max_categories: int = 3,
        max_memories: int = 5,
        max_record_chars: int = 3000,
        include_archived: bool = False,
        show_scores: bool = True,
    ) -> dict[str, Any]:
        """Preview memory context for a query.

        Pure read-only scoring. No LLM calls, no writes, no side effects.
        Uses the same scoring algorithm as load_memory_context but with
        explicit home parameter.

        Returns a DTO dict with matched categories, memories, and scores.
        """
        if not self.is_available():
            raise MemoryUnavailableError()

        query = query.strip()
        if not query:
            return {
                "query": "",
                "matchedCategories": [],
                "memories": [],
                "limits": {
                    "maxCategories": max_categories,
                    "maxMemories": max_memories,
                    "maxRecordChars": max_record_chars,
                },
                "sideEffects": False,
            }

        # Score categories
        try:
            categories = active_root_categories(
                self._home,
                include_all=include_archived,
            )
        except Exception:
            raise MemoryUnavailableError()

        scored_categories = [
            ScoredCategory(category=cat, score=score_category(query, cat))
            for cat in categories.values()
        ]
        matched_categories = [
            entry for entry in scored_categories if entry.score > 0
        ]

        # Select top categories
        if matched_categories:
            selected_categories = sorted(
                matched_categories,
                key=lambda entry: (
                    -entry.score,
                    _importance_rank(entry.category.fields.get("priority", "")),
                    entry.category.name,
                ),
            )[:max_categories]
        else:
            # No matches — select top by priority
            selected_categories = sorted(
                scored_categories,
                key=lambda entry: (
                    -entry.score,
                    _importance_rank(entry.category.fields.get("priority", "")),
                    entry.category.name,
                ),
            )[:max_categories]

        selected_names = {entry.category.name for entry in selected_categories}
        if not matched_categories and categories:
            selected_names = set(categories)

        # Score memory items
        candidates: list[MemoryItem] = []
        for category_name in selected_names:
            try:
                items = parse_index(category_name, self._home)
            except Exception:
                continue
            for item in items:
                status = item.fields.get("status", "")
                if not include_archived and status not in ("active", ""):
                    continue
                candidates.append(item)

        scored_items: list[tuple[MemoryItem, int]] = []
        for item in candidates:
            score = score_memory_item(query, item)
            if score > 0:
                scored_items.append((item, score))

        scored_items.sort(
            key=lambda pair: (
                -pair[1],
                _importance_rank(pair[0].fields.get("importance", "")),
                pair[0].memory_id,
            )
        )

        loaded: list[ScoredMemory] = []
        for item, score in scored_items[:max_memories]:
            record_text = ""
            truncated = False
            storage = item.storage
            if storage:
                try:
                    record_path = resolve_memory_uri(storage, self._home)
                    if record_path.exists():
                        text = record_path.read_text(encoding="utf-8")
                        record_text, truncated = _truncate_text(
                            text, max_record_chars
                        )
                except (ValueError, OSError):
                    pass
            loaded.append(
                ScoredMemory(
                    item=item,
                    score=score,
                    record_text=record_text,
                    truncated=truncated,
                )
            )

        # Filter categories to those that actually had matches
        if loaded:
            loaded_cat_names = {entry.item.category for entry in loaded}
            final_categories = [
                entry for entry in scored_categories
                if entry.category.name in loaded_cat_names
            ]
            final_categories.sort(
                key=lambda entry: (
                    -entry.score,
                    _importance_rank(entry.category.fields.get("priority", "")),
                    entry.category.name,
                ),
            )
            selected_categories = final_categories[:max_categories]

        return {
            "query": query,
            "matchedCategories": [
                _transform_scored_category_dto(entry)
                for entry in selected_categories
            ],
            "memories": [
                _transform_scored_memory_dto(entry)
                for entry in loaded
            ],
            "limits": {
                "maxCategories": max_categories,
                "maxMemories": max_memories,
                "maxRecordChars": max_record_chars,
            },
            "sideEffects": False,
        }

    # ── Validation helpers ──

    @staticmethod
    def validate_memory_id(memory_id: str) -> str | None:
        """Validate a memory ID string.

        Returns None if valid, or an error description string if invalid.
        """
        if not memory_id:
            return "Memory ID is required."
        if len(memory_id) > _MAX_MEMORY_ID_LENGTH:
            return "Memory ID is too long."
        if not MEMORY_ID_RE.match(memory_id):
            return "Memory ID format is invalid."
        return None
