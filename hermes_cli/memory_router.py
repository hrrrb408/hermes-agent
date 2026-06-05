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

ROOT_TEMPLATE = """# Hermes Memory Root Router

This file is the root router of Hermes memory.
It only stores memory categories and category index locations.
Detailed memory records are stored under memory/records/.

## user

- index: memory://indexes/user.md
- scope: user
- priority: P0
- keywords: user, profile, habit, preference
- description: 用户身份、长期偏好、使用习惯、沟通风格等。

## hermes

- index: memory://indexes/hermes.md
- scope: project
- priority: P0
- keywords: Hermes, dev-check, gateway, memory, cli
- description: Hermes 项目当前进度、开发约束、设计决策、功能规划等。

## projects

- index: memory://indexes/projects.md
- scope: project
- priority: P1
- keywords: project, software, requirement, design, progress
- description: 用户其他软件项目的需求、设计、进度和技术栈。

## learning

- index: memory://indexes/learning.md
- scope: learning
- priority: P1
- keywords: learning, roadmap, progress, chapter
- description: 用户长期学习路线、已学章节、下一步学习计划等。

## dev-env

- index: memory://indexes/dev-env.md
- scope: environment
- priority: P1
- keywords: macOS, Java, Python, Rust, Node, MySQL, path
- description: 用户本地开发环境、工具链、路径、版本、注意事项等。

## preferences

- index: memory://indexes/preferences.md
- scope: preference
- priority: P0
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

    for category in ("user", "projects", "learning", "dev-env", "preferences"):
        index = mem_dir / "indexes" / f"{category}.md"
        if not index.exists():
            title = category.replace("-", " ").title()
            index.write_text(
                EMPTY_INDEX_TEMPLATE.format(title=title, category=category),
                encoding="utf-8",
            )


def append_event(action: str, memory_id: str, category: str, summary: str, home: Path | None = None) -> None:
    home = home or get_hermes_home()
    ensure_memory_scaffold(home)
    event = {
        "time": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "action": action,
        "memory_id": memory_id,
        "category": category,
        "summary": summary,
    }
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


def parse_root(home: Path | None = None) -> dict[str, RootCategory]:
    root = memory_root(home)
    text = root.read_text(encoding="utf-8")
    categories: dict[str, RootCategory] = {}
    for name, lines in _split_sections(text):
        fields = _parse_bullet_fields(lines)
        categories[name] = RootCategory(name=name, fields=fields)
    return categories


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


def list_items(home: Path | None = None) -> list[MemoryItem]:
    items: list[MemoryItem] = []
    for category in parse_root(home):
        items.extend(parse_index(category, home))
    return items


def find_item(memory_id: str, home: Path | None = None) -> MemoryItem | None:
    for item in list_items(home):
        if item.memory_id == memory_id:
            return item
    return None


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
        categories = parse_root(home)
    except Exception as exc:
        add(False, "MEMORY.md root router format valid", str(exc))
        return MemoryCheckResult(ok=False, checks=checks, lines=lines, failures=failures)

    add(bool(categories), "MEMORY.md root router format valid", f"{len(categories)} categories")

    seen_ids: dict[str, str] = {}
    duplicate_ids: list[str] = []
    index_refs_ok = True
    indexes_valid = True
    records_ok = True
    importance_ok = True
    ttl_ok = True
    status_ok = True

    for category, entry in categories.items():
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

    add(index_refs_ok, "root index refs valid", "ok" if index_refs_ok else "see failures")
    add(indexes_valid, "category index files valid", "ok" if indexes_valid else "see failures")
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


def cmd_memory_root(args) -> None:
    ensure_memory_scaffold()
    print(memory_root().read_text(encoding="utf-8"))


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
    items = list_items()
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
    candidates.extend(sorted((mem_dir / "indexes").glob("*.md")))
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
