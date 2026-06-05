"""Hierarchical memory router helpers.

This module is intentionally file-based and dependency-light.  It does not
perform summarization, embedding, context injection, or gateway work.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from hermes_constants import get_hermes_home


VALID_IMPORTANCE = {"P0", "P1", "P2", "P3"}
VALID_TTL = {"permanent", "project", "session", "temporary"}
VALID_STATUS = {"active", "archived", "deprecated", "superseded", "conflict"}
VALID_CATEGORY_STATUS = {"active", "archived", "deprecated"}
CATEGORY_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
MEMORY_ID_RE = re.compile(r"^MEM-[A-Z0-9][A-Z0-9_-]*-[0-9]{3,}$")

ROOT_TEMPLATE = """# Hermes Memory Root Router

This file is the root router of Hermes memory.
It only stores memory categories and category index locations.
Detailed memory records are stored under memory/records/.

## user

- index: memory://indexes/user.md
- scope: user
- priority: P0
- status: active
- keywords: user, profile, habit, preference
- description: 用户身份、长期偏好、使用习惯、沟通风格等。

## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- status: active
- keywords: Hermes, dev-check, gateway, memory, cli
- description: Hermes 项目当前进度、开发约束、设计决策、功能规划等。

## projects

- index: memory://indexes/projects.md
- scope: project
- priority: P1
- status: active
- keywords: project, software, requirement, design, progress
- description: 用户其他软件项目的需求、设计、进度和技术栈。

## learning

- index: memory://indexes/learning.md
- scope: learning
- priority: P1
- status: active
- keywords: learning, roadmap, progress, chapter
- description: 用户长期学习路线、已学章节、下一步学习计划等。

## dev-env

- index: memory://indexes/dev-env.md
- scope: environment
- priority: P1
- status: active
- keywords: macOS, Java, Python, Rust, Node, MySQL, path
- description: 用户本地开发环境、工具链、路径、版本、注意事项等。

## preferences

- index: memory://indexes/preferences.md
- scope: preference
- priority: P0
- status: active
- keywords: answer style, engineering process, code explanation
- description: 用户对回答风格、项目分析方式、代码讲解方式的长期偏好。
"""

EMPTY_INDEX_TEMPLATE = """# {title} Memory Index

This file stores category-level memory indexes for {category} memories.
"""


@dataclass
class RootCategory:
    name: str
    fields: dict[str, str]


@dataclass
class MemoryItem:
    memory_id: str
    title: str
    category: str
    fields: dict[str, str]

    @property
    def storage(self) -> str:
        return self.fields.get("storage", "")


@dataclass
class MemoryCheckResult:
    ok: bool
    checks: list[tuple[str, str, str]]
    lines: list[str]
    failures: list[str]


def memory_root(home: Path | None = None) -> Path:
    return (home or get_hermes_home()) / "MEMORY.md"


def memory_dir(home: Path | None = None) -> Path:
    return (home or get_hermes_home()) / "memory"


def resolve_memory_uri(uri: str, home: Path | None = None) -> Path:
    if not uri.startswith("memory://"):
        raise ValueError(f"invalid memory URI: {uri}")
    rel = uri.removeprefix("memory://").strip()
    if not rel or rel.startswith("/") or ".." in Path(rel).parts:
        raise ValueError(f"unsafe memory URI: {uri}")
    return memory_dir(home) / rel


def _is_memory_path(path: Path, home: Path | None = None) -> bool:
    try:
        path.resolve().relative_to(memory_dir(home).resolve())
        return True
    except ValueError:
        return False


def ensure_memory_scaffold(home: Path | None = None) -> None:
    home = home or get_hermes_home()
    mem_dir = memory_dir(home)
    (mem_dir / "indexes").mkdir(parents=True, exist_ok=True)
    (mem_dir / "records").mkdir(parents=True, exist_ok=True)
    (mem_dir / "snapshots").mkdir(parents=True, exist_ok=True)
    events = mem_dir / "events.jsonl"
    if not events.exists():
        events.write_text("", encoding="utf-8")

    root = memory_root(home)
    if not root.exists():
        root.write_text(ROOT_TEMPLATE, encoding="utf-8")

    for category in parse_root(home):
        index = mem_dir / "indexes" / f"{category}.md"
        if not index.exists():
            title = category.replace("-", " ").title()
            index.write_text(
                EMPTY_INDEX_TEMPLATE.format(title=title, category=category),
                encoding="utf-8",
            )


def append_event(
    action: str,
    category: str,
    summary: str,
    home: Path | None = None,
    *,
    memory_id: str | None = None,
    index: str | None = None,
    storage: str | None = None,
) -> None:
    home = home or get_hermes_home()
    ensure_memory_scaffold(home)
    event = {
        "time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "action": action,
        "category": category,
        "summary": summary,
    }
    if memory_id:
        event["memory_id"] = memory_id
    if index:
        event["index"] = index
    if storage:
        event["storage"] = storage
    with (memory_dir(home) / "events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def _parse_bullet_fields(lines: Iterable[str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in lines:
        match = re.match(r"^-\s+([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line.strip())
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _split_sections(text: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+?)\s*$", line)
        if heading:
            if current_title is not None:
                sections.append((current_title, current_lines))
            current_title = heading.group(1).strip()
            current_lines = []
        elif current_title is not None:
            current_lines.append(line)
    if current_title is not None:
        sections.append((current_title, current_lines))
    return sections


def _document_header(text: str) -> str:
    first_heading = re.search(r"^##\s+", text, flags=re.MULTILINE)
    if first_heading:
        return text[: first_heading.start()].rstrip() + "\n"
    return text.rstrip() + "\n"


def _today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _slug(value: str) -> str:
    lowered = value.casefold()
    chars: list[str] = []
    for char in lowered:
        if char.isascii() and char.isalnum():
            chars.append(char)
        elif char in {"-", "_"}:
            chars.append(char)
        elif char.isspace():
            chars.append("-")
    slug = re.sub(r"-+", "-", "".join(chars)).strip("-_")
    return slug or "memory"


def validate_memory_id(memory_id: str) -> None:
    if not MEMORY_ID_RE.match(memory_id):
        raise ValueError(
            f"invalid memory id: {memory_id!r}. Must match MEM-<NAME>-<NNN>"
        )


def validate_memory_fields(*, importance: str, ttl: str, status: str, tags: str, summary: str) -> None:
    if importance not in VALID_IMPORTANCE:
        raise ValueError(f"Invalid importance: {importance}")
    if ttl not in VALID_TTL:
        raise ValueError(f"Invalid ttl: {ttl}")
    if status not in VALID_STATUS:
        raise ValueError(f"Invalid status: {status}")
    if not _normalize_keywords(tags):
        raise ValueError("tags cannot be empty")
    if not summary.strip():
        raise ValueError("summary cannot be empty")


def parse_root(home: Path | None = None) -> dict[str, RootCategory]:
    root = memory_root(home)
    text = root.read_text(encoding="utf-8")
    categories: dict[str, RootCategory] = {}
    for name, lines in _split_sections(text):
        fields = _parse_bullet_fields(lines)
        categories[name] = RootCategory(name=name, fields=fields)
    return categories


def parse_root_sections(home: Path | None = None) -> list[RootCategory]:
    root = memory_root(home)
    text = root.read_text(encoding="utf-8")
    return [
        RootCategory(name=name, fields=_parse_bullet_fields(lines))
        for name, lines in _split_sections(text)
    ]


def active_root_categories(
    home: Path | None = None,
    *,
    include_all: bool = False,
) -> dict[str, RootCategory]:
    categories = parse_root(home)
    if include_all:
        return categories
    return {
        name: category
        for name, category in categories.items()
        if category.fields.get("status", "active") == "active"
    }


def validate_category_name(name: str) -> None:
    if not CATEGORY_NAME_RE.match(name):
        raise ValueError(
            f"invalid category name: {name!r}. Must match [a-z0-9][a-z0-9_-]*"
        )


def _normalize_keywords(keywords: str) -> str:
    return ", ".join(part.strip() for part in keywords.split(",") if part.strip())


def _category_title(category: str) -> str:
    return category.replace("-", " ").replace("_", " ").title()


def _root_header() -> str:
    root = memory_root()
    text = root.read_text(encoding="utf-8")
    first_heading = re.search(r"^##\s+", text, flags=re.MULTILINE)
    if first_heading:
        return text[: first_heading.start()].rstrip() + "\n"
    return text.rstrip() + "\n"


def _render_root(categories: Iterable[RootCategory]) -> str:
    parts = [_root_header().rstrip(), ""]
    for category in categories:
        fields = category.fields
        parts.extend(
            [
                f"## {category.name}",
                "",
                f"- index: {fields.get('index', f'memory://indexes/{category.name}.md')}",
                f"- scope: {fields.get('scope', 'custom')}",
                f"- priority: {fields.get('priority', 'P2')}",
                f"- status: {fields.get('status', 'active')}",
                f"- keywords: {fields.get('keywords', category.name)}",
                f"- description: {fields.get('description', '')}",
                "",
            ]
        )
    return "\n".join(parts).rstrip() + "\n"


def backup_memory_root(home: Path | None = None) -> Path:
    home = home or get_hermes_home()
    ensure_memory_scaffold(home)
    snapshots = memory_dir(home) / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = snapshots / f"MEMORY-{stamp}.md"
    counter = 1
    while backup.exists():
        backup = snapshots / f"MEMORY-{stamp}-{counter}.md"
        counter += 1
    backup.write_text(memory_root(home).read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def backup_file(path: Path, prefix: str, home: Path | None = None) -> Path:
    home = home or get_hermes_home()
    ensure_memory_scaffold(home)
    snapshots = memory_dir(home) / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_prefix = re.sub(r"[^A-Za-z0-9_-]+", "-", prefix).strip("-") or "MEMORY"
    backup = snapshots / f"{safe_prefix}-{stamp}{path.suffix or '.bak'}"
    counter = 1
    while backup.exists():
        backup = snapshots / f"{safe_prefix}-{stamp}-{counter}{path.suffix or '.bak'}"
        counter += 1
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def write_root_categories(categories: Iterable[RootCategory], home: Path | None = None) -> None:
    home = home or get_hermes_home()
    memory_root(home).write_text(_render_root(categories), encoding="utf-8")


def ensure_root_status_fields(home: Path | None = None) -> bool:
    """Backfill missing category status fields. Returns True when changed."""
    home = home or get_hermes_home()
    ensure_memory_scaffold(home)
    categories = parse_root_sections(home)
    if all(category.fields.get("status") for category in categories):
        return False
    backup_memory_root(home)
    for category in categories:
        category.fields.setdefault("status", "active")
    write_root_categories(categories, home)
    append_event(
        "category_status_backfill",
        "root",
        "Backfilled missing root category status fields",
        home,
    )
    return True


def parse_index(category: str, home: Path | None = None) -> list[MemoryItem]:
    categories = parse_root(home)
    if category not in categories:
        raise KeyError(f"memory category not found: {category}")
    index_uri = categories[category].fields.get("index", "")
    index_path = resolve_memory_uri(index_uri, home)
    text = index_path.read_text(encoding="utf-8")
    items: list[MemoryItem] = []
    for title, lines in _split_sections(text):
        match = re.match(r"^(MEM-[A-Z0-9_-]+-\d+)\s+(.+)$", title)
        if not match:
            continue
        items.append(
            MemoryItem(
                memory_id=match.group(1),
                title=match.group(2).strip(),
                category=category,
                fields=_parse_bullet_fields(lines),
            )
        )
    return items


def category_index_path(category: str, home: Path | None = None) -> Path:
    categories = parse_root(home)
    if category not in categories:
        raise KeyError(f"memory category not found: {category}")
    return resolve_memory_uri(categories[category].fields.get("index", ""), home)


def _render_index_item(item: MemoryItem) -> str:
    fields = item.fields
    ordered = [
        "type",
        "importance",
        "ttl",
        "status",
        "tags",
        "storage",
        "created_at",
        "updated_at",
        "summary",
    ]
    lines = [f"## {item.memory_id} {item.title}", ""]
    for field in ordered:
        lines.append(f"- {field}: {fields.get(field, '')}")
    return "\n".join(lines).rstrip()


def write_index_items(category: str, items: list[MemoryItem], home: Path | None = None) -> None:
    path = category_index_path(category, home)
    header = _document_header(path.read_text(encoding="utf-8"))
    parts = [header.rstrip()]
    for item in items:
        parts.extend(["", _render_index_item(item)])
    path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")


def find_item_location(memory_id: str, home: Path | None = None) -> tuple[MemoryItem, Path, list[MemoryItem]] | None:
    for category in parse_root(home):
        items = parse_index(category, home)
        for item in items:
            if item.memory_id == memory_id:
                return item, category_index_path(category, home), items
    return None


def list_items(home: Path | None = None, *, include_all: bool = False) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    for category in active_root_categories(home, include_all=include_all):
        for item in parse_index(category, home):
            if include_all or item.fields.get("status") == "active":
                items.append(item)
    return items


def find_item(memory_id: str, home: Path | None = None) -> MemoryItem | None:
    for item in list_items(home, include_all=True):
        if item.memory_id == memory_id:
            return item
    return None


def _record_uri_for(category: str, memory_id: str, title: str) -> str:
    if category == "hermes":
        return f"memory://records/projects/hermes/{memory_id.casefold()}.md"
    return f"memory://records/{category}/{memory_id.casefold()}.md"


def _validate_record_uri(uri: str, home: Path | None = None) -> Path:
    if not uri.startswith("memory://records/"):
        raise ValueError(f"Invalid storage path: {uri}")
    path = resolve_memory_uri(uri, home)
    if not _is_memory_path(path, home):
        raise ValueError(f"Invalid storage path: {uri}")
    return path


def _record_body_from_text(text: str) -> str:
    match = re.search(
        r"^## Details\s*\n(?P<body>.*?)(?=^## Metadata\s*$|\Z)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match:
        return match.group("body").strip()
    return ""


def _render_record(item: MemoryItem, body: str) -> str:
    fields = item.fields
    details = body.strip() or "No details provided yet."
    return f"""# {item.memory_id} {item.title}

## Summary

{fields.get("summary", "")}

## Details

{details}

## Metadata

- category: {item.category}
- type: {fields.get("type", "")}
- importance: {fields.get("importance", "")}
- ttl: {fields.get("ttl", "")}
- status: {fields.get("status", "")}
- tags: {fields.get("tags", "")}
- created_at: {fields.get("created_at", "")}
- updated_at: {fields.get("updated_at", "")}
"""


def create_memory_item(args) -> tuple[MemoryItem, str]:
    ensure_memory_scaffold()
    category = args.category
    categories = parse_root()
    if category not in categories:
        raise ValueError(f"Category not found: {category}")
    category_status = categories[category].fields.get("status", "active")
    if category_status != "active":
        raise ValueError(f"Category is {category_status}: {category}")

    memory_id = args.memory_id
    validate_memory_id(memory_id)
    if find_item(memory_id) is not None:
        raise ValueError(f"Duplicate memory id: {memory_id}")

    tags = _normalize_keywords(args.tags)
    validate_memory_fields(
        importance=args.importance,
        ttl=args.ttl,
        status="active",
        tags=tags,
        summary=args.summary,
    )

    storage = args.record_path or _record_uri_for(category, memory_id, args.title)
    record_path = _validate_record_uri(storage)
    if record_path.exists():
        raise FileExistsError(f"Record file already exists: {storage}")

    index_path = category_index_path(category)
    backup_file(index_path, f"INDEX-{category}")

    today = _today()
    item = MemoryItem(
        memory_id=memory_id,
        title=args.title,
        category=category,
        fields={
            "type": args.type,
            "importance": args.importance,
            "ttl": args.ttl,
            "status": "active",
            "tags": tags,
            "storage": storage,
            "created_at": today,
            "updated_at": today,
            "summary": args.summary,
        },
    )
    items = parse_index(category)
    items.append(item)
    write_index_items(category, items)

    record_path.parent.mkdir(parents=True, exist_ok=True)
    body = args.body or args.summary
    record_path.write_text(_render_record(item, body), encoding="utf-8")
    append_event(
        "memory_create",
        category,
        f"Created memory {memory_id}",
        memory_id=memory_id,
        storage=storage,
    )
    return item, categories[category].fields.get("index", "")


def update_memory_item(args, *, archive: bool = False) -> MemoryItem:
    ensure_memory_scaffold()
    location = find_item_location(args.memory_id)
    if location is None:
        raise ValueError(f"Memory not found: {args.memory_id}")
    item, index_path, items = location
    record_path = _validate_record_uri(item.storage)
    if not record_path.exists():
        raise FileNotFoundError(f"Memory record not found: {item.storage}")

    if archive and item.fields.get("status") == "archived":
        return item

    updates: dict[str, str] = {}
    for field in ("title", "type", "importance", "ttl", "status", "tags", "summary"):
        value = getattr(args, field, None)
        if value is None:
            continue
        updates[field] = _normalize_keywords(value) if field == "tags" else value
    if archive:
        updates["status"] = "archived"
    if "importance" in updates and updates["importance"] not in VALID_IMPORTANCE:
        raise ValueError(f"Invalid importance: {updates['importance']}")
    if "ttl" in updates and updates["ttl"] not in VALID_TTL:
        raise ValueError(f"Invalid ttl: {updates['ttl']}")
    if "status" in updates and updates["status"] not in VALID_STATUS:
        raise ValueError(f"Invalid status: {updates['status']}")
    if "tags" in updates and not updates["tags"]:
        raise ValueError("tags cannot be empty")
    if "summary" in updates and not updates["summary"].strip():
        raise ValueError("summary cannot be empty")

    if not updates and getattr(args, "body", None) is None:
        return item

    backup_file(index_path, f"INDEX-{item.category}")
    backup_file(record_path, f"RECORD-{item.memory_id}")

    if "title" in updates:
        item.title = updates.pop("title")
    item.fields.update(updates)
    item.fields["updated_at"] = _today()
    write_index_items(item.category, items)

    existing_text = record_path.read_text(encoding="utf-8")
    body = getattr(args, "body", None)
    if body is None:
        body = _record_body_from_text(existing_text) or item.fields.get("summary", "")
    record_path.write_text(_render_record(item, body), encoding="utf-8")
    append_event(
        "memory_archive" if archive else "memory_update",
        item.category,
        f"{'Archived' if archive else 'Updated'} memory {item.memory_id}",
        memory_id=item.memory_id,
        storage=item.storage,
    )
    return item


def validate_memory(home: Path | None = None) -> MemoryCheckResult:
    home = home or get_hermes_home()
    checks: list[tuple[str, str, str]] = []
    lines: list[str] = []
    failures: list[str] = []

    def add(ok: bool, label: str, detail: str) -> None:
        status = "PASS" if ok else "FAIL"
        checks.append((status, label, detail))
        lines.append(f"{status:<4} {label + ':':<30} {detail}")
        if not ok:
            failures.append(f"{label}: {detail}")

    root = memory_root(home)
    mem_dir = memory_dir(home)
    add(root.exists(), "MEMORY.md exists", str(root))
    add(mem_dir.is_dir(), "memory/ exists", str(mem_dir))
    add((mem_dir / "indexes").is_dir(), "memory/indexes/ exists", str(mem_dir / "indexes"))
    add((mem_dir / "records").is_dir(), "memory/records/ exists", str(mem_dir / "records"))
    add((mem_dir / "snapshots").is_dir(), "memory/snapshots/ exists", str(mem_dir / "snapshots"))
    add((mem_dir / "events.jsonl").exists(), "memory/events.jsonl exists", str(mem_dir / "events.jsonl"))

    if not root.exists():
        return MemoryCheckResult(ok=False, checks=checks, lines=lines, failures=failures)

    try:
        root_sections = parse_root_sections(home)
        categories = {category.name: category for category in root_sections}
    except Exception as exc:
        add(False, "root categories parseable", str(exc))
        return MemoryCheckResult(ok=False, checks=checks, lines=lines, failures=failures)

    add(bool(root_sections), "root categories parseable", f"{len(root_sections)} categories")

    duplicate_categories = sorted({
        category.name
        for category in root_sections
        if [entry.name for entry in root_sections].count(category.name) > 1
    })
    add(
        not duplicate_categories,
        "no duplicate category names",
        "ok" if not duplicate_categories else ", ".join(duplicate_categories),
    )

    seen_ids: dict[str, str] = {}
    duplicate_ids: list[str] = []
    category_names_ok = True
    category_status_ok = True
    category_priority_ok = True
    index_refs_ok = True
    indexes_valid = True
    records_ok = True
    importance_ok = True
    ttl_ok = True
    status_ok = True

    for category, entry in categories.items():
        if not CATEGORY_NAME_RE.match(category):
            category_names_ok = False
            failures.append(f"{category}: invalid category name")
        if entry.fields.get("priority") not in VALID_IMPORTANCE:
            category_priority_ok = False
            failures.append(f"{category}: invalid priority {entry.fields.get('priority')!r}")
        if entry.fields.get("status", "active") not in VALID_CATEGORY_STATUS:
            category_status_ok = False
            failures.append(f"{category}: invalid status {entry.fields.get('status')!r}")
        for field in ("index", "scope", "priority", "status", "keywords", "description"):
            if not entry.fields.get(field):
                index_refs_ok = False
                failures.append(f"{category}: missing root field {field}")

        index_uri = entry.fields.get("index", "")
        if not index_uri.startswith("memory://indexes/"):
            index_refs_ok = False
            failures.append(f"{category}: invalid index URI {index_uri!r}")
            continue
        try:
            index_path = resolve_memory_uri(index_uri, home)
        except ValueError as exc:
            index_refs_ok = False
            failures.append(f"{category}: {exc}")
            continue
        if not index_path.exists():
            index_refs_ok = False
            failures.append(f"{category}: missing index {index_uri}")
            continue
        try:
            items = parse_index(category, home)
        except Exception as exc:
            indexes_valid = False
            failures.append(f"{category}: invalid index {index_uri}: {exc}")
            continue
        for item in items:
            if item.memory_id in seen_ids:
                duplicate_ids.append(item.memory_id)
            seen_ids[item.memory_id] = category

            for field in ("type", "importance", "ttl", "status", "tags", "storage", "created_at", "updated_at", "summary"):
                if not item.fields.get(field):
                    indexes_valid = False
                    failures.append(f"{item.memory_id}: missing {field}")
            if item.fields.get("importance") not in VALID_IMPORTANCE:
                importance_ok = False
                failures.append(f"{item.memory_id}: invalid importance {item.fields.get('importance')!r}")
            if item.fields.get("ttl") not in VALID_TTL:
                ttl_ok = False
                failures.append(f"{item.memory_id}: invalid ttl {item.fields.get('ttl')!r}")
            if item.fields.get("status") not in VALID_STATUS:
                status_ok = False
                failures.append(f"{item.memory_id}: invalid status {item.fields.get('status')!r}")

            storage = item.fields.get("storage", "")
            if not storage.startswith("memory://records/"):
                records_ok = False
                failures.append(f"{item.memory_id}: invalid storage URI {storage!r}")
                continue
            try:
                record_path = resolve_memory_uri(storage, home)
            except ValueError as exc:
                records_ok = False
                failures.append(f"{item.memory_id}: {exc}")
                continue
            if not record_path.exists():
                records_ok = False
                failures.append(f"{item.memory_id}: missing record {storage}")

    add(category_names_ok, "category names valid", "ok" if category_names_ok else "see failures")
    add(category_status_ok, "category status valid", "ok" if category_status_ok else "see failures")
    add(category_priority_ok, "category priority valid", "ok" if category_priority_ok else "see failures")
    add(index_refs_ok, "category indexes valid", "ok" if index_refs_ok else "see failures")
    add(index_refs_ok, "category index refs exist", "ok" if index_refs_ok else "see failures")
    add(indexes_valid, "category index files parseable", "ok" if indexes_valid else "see failures")
    add(records_ok, "record refs valid", "ok" if records_ok else "see failures")
    add(not duplicate_ids, "memory_id unique", "ok" if not duplicate_ids else ", ".join(sorted(set(duplicate_ids))))
    add(importance_ok, "importance values valid", "ok" if importance_ok else "see failures")
    add(ttl_ok, "ttl values valid", "ok" if ttl_ok else "see failures")
    add(status_ok, "status values valid", "ok" if status_ok else "see failures")

    return MemoryCheckResult(ok=not failures, checks=checks, lines=lines, failures=failures)


def print_memory_check(home: Path | None = None) -> int:
    result = validate_memory(home)
    print()
    print("Hermes memory check")
    print("────────────────────────────────────────")
    for line in result.lines:
        print(line)
    if result.failures:
        print()
        print("Failures:")
        for failure in result.failures:
            print(f"- {failure}")
    print("────────────────────────────────────────")
    print(f"Result: {'PASS' if result.ok else 'FAIL'}")
    print()
    return 0 if result.ok else 1


def _print_categories(categories: Iterable[RootCategory]) -> None:
    print()
    print("Memory categories")
    print("────────────────────────────────────────")
    for category in categories:
        fields = category.fields
        print(category.name)
        print(f"  index:       {fields.get('index', '')}")
        print(f"  scope:       {fields.get('scope', '')}")
        print(f"  priority:    {fields.get('priority', '')}")
        print(f"  status:      {fields.get('status', 'active')}")
        print(f"  keywords:    {fields.get('keywords', '')}")
        print(f"  description: {fields.get('description', '')}")
    print()


def cmd_memory_root(args) -> None:
    ensure_memory_scaffold()
    categories = active_root_categories(include_all=getattr(args, "all", False))
    _print_categories(categories.values())


def cmd_memory_index(args) -> None:
    ensure_memory_scaffold()
    try:
        categories = parse_root()
        category = args.category
        if category not in categories:
            print(f"Error: memory category not found: {category}", file=sys.stderr)
            sys.exit(1)
        path = resolve_memory_uri(categories[category].fields["index"])
        print(path.read_text(encoding="utf-8"))
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_memory_list(args) -> None:
    ensure_memory_scaffold()
    items = list_items(include_all=getattr(args, "all", False))
    if not items:
        print("No memory items found.")
        return
    print()
    print("Memory items")
    print("────────────────────────────────────────")
    for item in items:
        print(f"{item.memory_id} {item.title}")
        print(f"  category:   {item.category}")
        print(f"  importance: {item.fields.get('importance', '')}")
        print(f"  ttl:        {item.fields.get('ttl', '')}")
        print(f"  status:     {item.fields.get('status', '')}")
        print(f"  tags:       {item.fields.get('tags', '')}")
        print(f"  storage:    {item.storage}")
        print(f"  summary:    {item.fields.get('summary', '')}")
    print()


def cmd_memory_show(args) -> None:
    ensure_memory_scaffold()
    item = find_item(args.memory_id)
    if item is None:
        print(f"Error: memory_id not found: {args.memory_id}", file=sys.stderr)
        sys.exit(1)
    try:
        path = resolve_memory_uri(item.storage)
    except ValueError as exc:
        print(f"Error: {item.memory_id} has invalid storage: {exc}", file=sys.stderr)
        sys.exit(1)
    if not path.exists():
        print(f"Error: memory record missing for {item.memory_id}: {item.storage}", file=sys.stderr)
        sys.exit(1)
    print(path.read_text(encoding="utf-8"))


def cmd_memory_search(args) -> None:
    ensure_memory_scaffold()
    query = args.query.strip()
    if not query:
        print("Error: query cannot be empty", file=sys.stderr)
        sys.exit(1)
    candidates = [memory_root()]
    mem_dir = memory_dir()
    candidates.extend(sorted((mem_dir / "indexes").rglob("*.md")))
    candidates.extend(sorted((mem_dir / "records").rglob("*.md")))

    matches = 0
    needle = query.casefold()
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        lower = text.casefold()
        pos = lower.find(needle)
        if pos < 0:
            continue
        matches += 1
        start = max(0, pos - 60)
        end = min(len(text), pos + len(query) + 80)
        snippet = " ".join(text[start:end].split())
        print(f"{path}: {snippet}")
    if matches == 0:
        print(f"No memory matches for: {query}")


def cmd_memory_check(args) -> None:
    sys.exit(print_memory_check())


def _print_write_result(header: str, item: MemoryItem, *, index: str | None = None) -> None:
    check = validate_memory()
    print()
    print(header)
    print()
    print(f"id: {item.memory_id}")
    print(f"category: {item.category}")
    if index:
        print(f"index: {index}")
    print(f"storage: {item.storage}")
    print(f"status: {item.fields.get('status', '')}")
    print()
    print(f"Result: {'PASS' if check.ok else 'FAIL'}")
    if check.failures:
        for failure in check.failures:
            print(f"- {failure}")
        sys.exit(1)


def cmd_memory_add(args) -> None:
    try:
        item, index = create_memory_item(args)
    except (ValueError, FileExistsError, KeyError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    _print_write_result("Memory added", item, index=index)


def cmd_memory_update(args) -> None:
    try:
        item = update_memory_item(args)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    _print_write_result("Memory updated", item)


def cmd_memory_archive(args) -> None:
    try:
        before = find_item(args.memory_id)
        item = update_memory_item(args, archive=True)
    except (ValueError, FileNotFoundError) as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    if before and before.fields.get("status") == "archived":
        print(f"Memory already archived: {args.memory_id}")
    _print_write_result("Memory archived", item)


def cmd_memory_category_list(args) -> None:
    ensure_memory_scaffold()
    categories = active_root_categories(include_all=getattr(args, "all", False))
    _print_categories(categories.values())


def cmd_memory_category_show(args) -> None:
    ensure_memory_scaffold()
    categories = parse_root()
    category = args.category
    if category not in categories:
        print(f"ERROR Category not found: {category}", file=sys.stderr)
        sys.exit(1)
    _print_categories([categories[category]])


def cmd_memory_category_add(args) -> None:
    ensure_memory_scaffold()
    category = args.category
    try:
        validate_category_name(category)
    except ValueError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        sys.exit(1)
    categories = parse_root_sections()
    if any(entry.name == category for entry in categories):
        print(f"ERROR Category already exists: {category}", file=sys.stderr)
        sys.exit(1)
    if args.priority not in VALID_IMPORTANCE:
        print(f"ERROR invalid priority: {args.priority}", file=sys.stderr)
        sys.exit(1)

    index_uri = f"memory://indexes/{category}.md"
    index_path = resolve_memory_uri(index_uri)
    backup_memory_root()
    categories.append(
        RootCategory(
            name=category,
            fields={
                "index": index_uri,
                "scope": args.scope,
                "priority": args.priority,
                "status": "active",
                "keywords": _normalize_keywords(args.keywords),
                "description": args.description,
            },
        )
    )
    write_root_categories(categories)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    if not index_path.exists():
        index_path.write_text(
            EMPTY_INDEX_TEMPLATE.format(title=_category_title(category), category=category),
            encoding="utf-8",
        )
    append_event(
        "category_create",
        category,
        f"Created memory root category {category}",
        index=index_uri,
    )
    print(f"Created memory category: {category}")
    print(f"Index: {index_uri}")
    print("Run `hermes memory-check` to verify memory references.")


def cmd_memory_category_update(args) -> None:
    ensure_memory_scaffold()
    category = args.category
    categories = parse_root_sections()
    target = next((entry for entry in categories if entry.name == category), None)
    if target is None:
        print(f"ERROR Category not found: {category}", file=sys.stderr)
        sys.exit(1)
    if args.priority and args.priority not in VALID_IMPORTANCE:
        print(f"ERROR invalid priority: {args.priority}", file=sys.stderr)
        sys.exit(1)
    if args.status and args.status not in VALID_CATEGORY_STATUS:
        print(f"ERROR invalid status: {args.status}", file=sys.stderr)
        sys.exit(1)

    changed = False
    for field in ("scope", "priority", "status", "description"):
        value = getattr(args, field, None)
        if value is not None:
            target.fields[field] = value
            changed = True
    if args.keywords is not None:
        target.fields["keywords"] = _normalize_keywords(args.keywords)
        changed = True
    if not changed:
        print(f"No category metadata changes for: {category}")
        return

    backup_memory_root()
    write_root_categories(categories)
    append_event(
        "category_update",
        category,
        f"Updated memory root category {category}",
    )
    print(f"Updated memory category: {category}")


def cmd_memory_category_archive(args) -> None:
    ensure_memory_scaffold()
    category = args.category
    categories = parse_root_sections()
    target = next((entry for entry in categories if entry.name == category), None)
    if target is None:
        print(f"ERROR Category not found: {category}", file=sys.stderr)
        sys.exit(1)
    if target.fields.get("status") == "archived":
        print(f"Category already archived: {category}")
        return
    backup_memory_root()
    target.fields["status"] = "archived"
    write_root_categories(categories)
    append_event(
        "category_archive",
        category,
        f"Archived memory root category {category}",
    )
    print(f"Archived memory category: {category}")
