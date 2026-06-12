"""Static Tool Execution Policy for the Hermes Dev WebUI.

This module implements an immutable, pure-static, default-deny policy governing
which tools may be considered for execution in the Dev WebUI Agent Run context.

Architecture constraints:
  - No dependency on FastAPI, Provider, SessionDB, Memory, or Tool Registry.
  - No filesystem, database, or network access at import time.
  - No thread or subprocess creation.
  - All data is defined as frozen literals and validated at module load time.

Phase: 1G-01 — Tool Inventory and Static Policy Module
Status: Frozen (Phase 1G-00 canonical source)
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Mapping


# ---------------------------------------------------------------------------
# 1. ToolRiskLevel — R0 through R5
# ---------------------------------------------------------------------------


class ToolRiskLevel(str, Enum):
    """Primary risk classification for a canonical tool.

    Each tool is assigned exactly one ``ToolRiskLevel`` equal to its highest
    actual risk.  Capability tags are orthogonal and may overlap, but they do
    not participate in the primary-risk total.
    """

    R0 = "R0"  # Pure computation — no I/O, no network, no state
    R1 = "R1"  # Read-only local query — filesystem read or local DB read
    R2 = "R2"  # Read-only external network — API calls, search, analysis
    R3 = "R3"  # Controlled write — file/message/state mutation
    R4 = "R4"  # Process / code execution — shell, browser, subagent
    R5 = "R5"  # High-risk system — cron, admin, IoT device control


RISK_RANK: Mapping[ToolRiskLevel, int] = MappingProxyType(
    {
        ToolRiskLevel.R0: 0,
        ToolRiskLevel.R1: 1,
        ToolRiskLevel.R2: 2,
        ToolRiskLevel.R3: 3,
        ToolRiskLevel.R4: 4,
        ToolRiskLevel.R5: 5,
    }
)


# ---------------------------------------------------------------------------
# 2. ToolCapability — orthogonal capability tags
# ---------------------------------------------------------------------------


class ToolCapability(str, Enum):
    """Capability tags describing what a tool *can* do.

    A tool may have multiple capabilities.  Only ``primary_risk`` is unique.
    """

    PURE_COMPUTE = "PURE_COMPUTE"
    LOCAL_FILE_READ = "LOCAL_FILE_READ"
    LOCAL_FILE_WRITE = "LOCAL_FILE_WRITE"
    DATABASE_READ = "DATABASE_READ"
    DATABASE_WRITE = "DATABASE_WRITE"
    NETWORK_READ = "NETWORK_READ"
    NETWORK_WRITE = "NETWORK_WRITE"
    PROCESS_EXECUTION = "PROCESS_EXECUTION"
    CODE_EXECUTION = "CODE_EXECUTION"
    BROWSER_CONTROL = "BROWSER_CONTROL"
    DESKTOP_CONTROL = "DESKTOP_CONTROL"
    CREDENTIAL_USE = "CREDENTIAL_USE"
    REMOTE_STATE_MUTATION = "REMOTE_STATE_MUTATION"
    MESSAGE_SEND = "MESSAGE_SEND"
    MEDIA_GENERATION = "MEDIA_GENERATION"
    ADMINISTRATIVE_ACTION = "ADMINISTRATIVE_ACTION"
    SCHEDULING = "SCHEDULING"
    SUB_AGENT_EXECUTION = "SUB_AGENT_EXECUTION"


# ---------------------------------------------------------------------------
# 3. Immutable data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolPolicyEntry:
    """Immutable policy record for one canonical tool."""

    canonical_name: str
    primary_risk: ToolRiskLevel
    capabilities: frozenset[ToolCapability]
    permanently_denied: bool
    candidate_allowlisted: bool
    statically_allowed: bool
    source: str  # relative module identifier — never absolute paths
    rationale: str


@dataclass(frozen=True, slots=True)
class ToolPolicyDecision:
    """Pure-function decision result for a tool policy query."""

    requested_name: str
    canonical_name: str | None
    known: bool
    permanently_denied: bool
    candidate_allowlisted: bool
    statically_allowed: bool
    allowed: bool
    primary_risk: ToolRiskLevel | None
    reason_code: str


# ---------------------------------------------------------------------------
# 4. Reason codes (frozen)
# ---------------------------------------------------------------------------

REASON_TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
REASON_TOOL_PERMANENTLY_DENIED = "TOOL_PERMANENTLY_DENIED"
REASON_TOOL_NOT_ALLOWED = "TOOL_NOT_ALLOWED"
REASON_TOOL_POLICY_INVALID = "TOOL_POLICY_INVALID"
REASON_TOOL_SCHEMA_POLICY_INVALID = "TOOL_SCHEMA_POLICY_INVALID"


# ---------------------------------------------------------------------------
# 5. Global limits (frozen constants)
# ---------------------------------------------------------------------------

# Argument payload limits
MAX_ARGUMENT_PAYLOAD_BYTES: int = 32 * 1024  # 32 KiB
MAX_ARGUMENT_NESTING_DEPTH: int = 8
MAX_ARGUMENT_STRING_LENGTH: int = 4000
MAX_ARGUMENT_ARRAY_LENGTH: int = 100

# Timeout limits (seconds)
DEFAULT_R0_TIMEOUT_SECONDS: int = 2
DEFAULT_R1_TIMEOUT_SECONDS: int = 5
MAX_TOOL_TIMEOUT_SECONDS: int = 30

# Concurrency and call limits
MAX_TOOL_CALLS_PER_RUN: int = 3
MAX_GLOBAL_TOOL_CONCURRENCY: int = 1
MAX_TOOL_CONCURRENCY_PER_RUN: int = 1

# Output limits (bytes)
MAX_SERIALIZED_OUTPUT_BYTES: int = 64 * 1024  # 64 KiB
MAX_AGENT_VISIBLE_OUTPUT_BYTES: int = 16 * 1024  # 16 KiB
MAX_WEB_PREVIEW_OUTPUT_BYTES: int = 8 * 1024  # 8 KiB


# ---------------------------------------------------------------------------
# 6. 71-tool Inventory — single source of truth
# ---------------------------------------------------------------------------

# The inventory is defined in risk-level groups for readability.
# It is merged into a single immutable mapping at the bottom of this block.

# --- R0 (1 tool) ---
_R0_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="clarify",
        primary_risk=ToolRiskLevel.R0,
        capabilities=frozenset({ToolCapability.PURE_COMPUTE}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=True,
        source="tools/clarify_tool.py",
        rationale="Purely interactive — asks user a question. No I/O, no network, no state mutation.",
    ),
)

# --- R1 (5 tools) ---
_R1_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="read_file",
        primary_risk=ToolRiskLevel.R1,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=False,
        source="tools/file_tools.py",
        rationale="Read-only file access. Candidate pending strict root-allowlist enforcement.",
    ),
    ToolPolicyEntry(
        canonical_name="search_files",
        primary_risk=ToolRiskLevel.R1,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=False,
        source="tools/file_tools.py",
        rationale="Read-only file search. Candidate pending strict root-allowlist enforcement.",
    ),
    ToolPolicyEntry(
        canonical_name="session_search",
        primary_risk=ToolRiskLevel.R1,
        capabilities=frozenset({ToolCapability.DATABASE_READ}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=False,
        source="tools/session_search_tool.py",
        rationale="Read-only FTS5 search on local SessionDB. Candidate pending output redaction.",
    ),
    ToolPolicyEntry(
        canonical_name="skill_view",
        primary_risk=ToolRiskLevel.R1,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=False,
        source="tools/skills_tool.py",
        rationale="Read-only skill content. Candidate pending path restriction.",
    ),
    ToolPolicyEntry(
        canonical_name="skills_list",
        primary_risk=ToolRiskLevel.R1,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ}),
        permanently_denied=False,
        candidate_allowlisted=True,
        statically_allowed=False,
        source="tools/skills_tool.py",
        rationale="Read-only skill directory listing. No path exposure, name + description only.",
    ),
)

# --- R2 (19 tools) ---
_R2_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="feishu_doc_read",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/feishu_doc_tool.py",
        rationale="Read-only Feishu document. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="feishu_drive_list_comment_replies",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/feishu_drive_tool.py",
        rationale="Read-only comment replies from Feishu Drive. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="feishu_drive_list_comments",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/feishu_drive_tool.py",
        rationale="Read-only document comments from Feishu Drive. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="ha_get_state",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/homeassistant_tool.py",
        rationale="Read-only Home Assistant entity state. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="ha_list_entities",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/homeassistant_tool.py",
        rationale="Read-only Home Assistant entity listing. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="ha_list_services",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/homeassistant_tool.py",
        rationale="Read-only Home Assistant service listing. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_list",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Read-only Linear task listing. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_show",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Read-only Linear task detail. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="mixture_of_agents",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/moa_tool.py",
        rationale="Read-only multi-LLM aggregation. External API + credentials + cost.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_albums",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Read-only Spotify album metadata. External API + OAuth.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_search",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Read-only Spotify catalog search. External API + OAuth.",
    ),
    ToolPolicyEntry(
        canonical_name="video_analyze",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset(
            {ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE, ToolCapability.LOCAL_FILE_READ}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/vision_tools.py",
        rationale="Read-only video analysis. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="vision_analyze",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset(
            {ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE, ToolCapability.LOCAL_FILE_READ}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/vision_tools.py",
        rationale="Read-only image analysis. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="web_extract",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/web_tools.py",
        rationale="Read-only web page extraction. External API + arbitrary URLs.",
    ),
    ToolPolicyEntry(
        canonical_name="web_search",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/web_tools.py",
        rationale="Read-only web search. External API + credentials + query leakage.",
    ),
    ToolPolicyEntry(
        canonical_name="x_search",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/x_search_tool.py",
        rationale="Read-only xAI search. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="yb_query_group_info",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/yuanbao_tools.py",
        rationale="Read-only Yuanbao group info. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="yb_query_group_members",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/yuanbao_tools.py",
        rationale="Read-only Yuanbao group members. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="yb_search_sticker",
        primary_risk=ToolRiskLevel.R2,
        capabilities=frozenset({ToolCapability.NETWORK_READ, ToolCapability.CREDENTIAL_USE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/yuanbao_tools.py",
        rationale="Read-only Yuanbao sticker search. External API + credentials.",
    ),
)

# --- R3 (26 tools) ---
_R3_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="discord",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_READ, ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/discord_tool.py",
        rationale="Read/write Discord messages. External API + credentials.",
    ),
    ToolPolicyEntry(
        canonical_name="feishu_drive_add_comment",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/feishu_drive_tool.py",
        rationale="Writes comment to Feishu Drive document. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="feishu_drive_reply_comment",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/feishu_drive_tool.py",
        rationale="Writes reply to Feishu Drive comment. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="image_generate",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {
                ToolCapability.NETWORK_WRITE,
                ToolCapability.LOCAL_FILE_WRITE,
                ToolCapability.CREDENTIAL_USE,
                ToolCapability.MEDIA_GENERATION,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/image_generation_tool.py",
        rationale="Generates images. External API + cost + filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_block",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Modifies Linear task status. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_comment",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Writes comment to Linear task. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_complete",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Marks Linear task done. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_create",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Creates new Linear task. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_heartbeat",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Updates Linear task timestamp. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_link",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Creates Linear task dependency. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="kanban_unblock",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/kanban_tools.py",
        rationale="Changes Linear task status. External API + state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="memory",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/memory_tool.py",
        rationale="Writes to MEMORY.md, USER.md, memory/records/. Filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="patch",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/file_tools.py",
        rationale="Modifies files via find-and-replace. Filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="send_message",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.MESSAGE_SEND, ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE}
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/send_message_tool.py",
        rationale="Sends messages to external platforms. External state mutation.",
    ),
    ToolPolicyEntry(
        canonical_name="skill_manage",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/skill_manager_tool.py",
        rationale="Creates/updates/deletes skill files. Filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_devices",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Spotify device management — transfer action mutates playback. External API.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_library",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Spotify library management — save/remove actions. External API.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_playback",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Spotify playback control — play/pause/skip/volume. External API.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_playlists",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Spotify playlist management — create/update/modify. External API.",
    ),
    ToolPolicyEntry(
        canonical_name="spotify_queue",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.REMOTE_STATE_MUTATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="plugins/spotify/__init__.py",
        rationale="Spotify queue management — add action. External API.",
    ),
    ToolPolicyEntry(
        canonical_name="text_to_speech",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.LOCAL_FILE_WRITE, ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/tts_tool.py",
        rationale="Generates audio file. External API + filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="todo",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE}),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/todo_tool.py",
        rationale="Writes to TODO.md in HERMES_HOME. Filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="video_generate",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.NETWORK_WRITE, ToolCapability.LOCAL_FILE_WRITE, ToolCapability.CREDENTIAL_USE, ToolCapability.MEDIA_GENERATION}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/video_generation_tool.py",
        rationale="Generates video. External API + cost + filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="write_file",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset({ToolCapability.LOCAL_FILE_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/file_tools.py",
        rationale="Writes/overwrites arbitrary files. Filesystem write.",
    ),
    ToolPolicyEntry(
        canonical_name="yb_send_dm",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.MESSAGE_SEND, ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/yuanbao_tools.py",
        rationale="Sends Yuanbao DM. External API + message send.",
    ),
    ToolPolicyEntry(
        canonical_name="yb_send_sticker",
        primary_risk=ToolRiskLevel.R3,
        capabilities=frozenset(
            {ToolCapability.MESSAGE_SEND, ToolCapability.NETWORK_WRITE, ToolCapability.CREDENTIAL_USE}
        ),
        permanently_denied=False,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/yuanbao_tools.py",
        rationale="Sends Yuanbao sticker. External API + message send.",
    ),
)

# --- R4 (17 tools) ---
_R4_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="browser_back",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Browser navigation. Controlled execution environment.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_cdp",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_cdp_tool.py",
        rationale="Raw Chrome DevTools Protocol. Arbitrary browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_click",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Clicks page elements. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_console",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset(
            {ToolCapability.BROWSER_CONTROL, ToolCapability.CODE_EXECUTION, ToolCapability.NETWORK_WRITE}
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Executes JS via expression param. Browser + code execution.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_dialog",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_dialog_tool.py",
        rationale="Native dialog interaction. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_get_images",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_READ}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Reads page images. Browser control environment.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_navigate",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Loads arbitrary URLs. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_press",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Keyboard input in browser. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_scroll",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Browser page scroll. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_snapshot",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_READ}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Reads browser accessibility tree. Browser control environment.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_type",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_WRITE}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Types into form fields. Browser control.",
    ),
    ToolPolicyEntry(
        canonical_name="browser_vision",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.BROWSER_CONTROL, ToolCapability.NETWORK_READ}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/browser_tool.py",
        rationale="Screenshots page. Browser control environment.",
    ),
    ToolPolicyEntry(
        canonical_name="computer_use",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset({ToolCapability.DESKTOP_CONTROL, ToolCapability.LOCAL_FILE_READ}),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/computer_use_tool.py",
        rationale="Full desktop control — mouse, keyboard, screenshots.",
    ),
    ToolPolicyEntry(
        canonical_name="delegate_task",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset(
            {
                ToolCapability.SUB_AGENT_EXECUTION,
                ToolCapability.PROCESS_EXECUTION,
                ToolCapability.NETWORK_WRITE,
                ToolCapability.LOCAL_FILE_READ,
                ToolCapability.LOCAL_FILE_WRITE,
                ToolCapability.CREDENTIAL_USE,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/delegate_tool.py",
        rationale="Spawns subagent processes with full tool access.",
    ),
    ToolPolicyEntry(
        canonical_name="execute_code",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset(
            {
                ToolCapability.CODE_EXECUTION,
                ToolCapability.PROCESS_EXECUTION,
                ToolCapability.LOCAL_FILE_READ,
                ToolCapability.LOCAL_FILE_WRITE,
                ToolCapability.NETWORK_WRITE,
                ToolCapability.CREDENTIAL_USE,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/code_execution_tool.py",
        rationale="Python code execution with tool access.",
    ),
    ToolPolicyEntry(
        canonical_name="process",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset(
            {ToolCapability.PROCESS_EXECUTION, ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE, ToolCapability.NETWORK_WRITE}
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/process_registry.py",
        rationale="Background process management including stdin write and kill.",
    ),
    ToolPolicyEntry(
        canonical_name="terminal",
        primary_risk=ToolRiskLevel.R4,
        capabilities=frozenset(
            {ToolCapability.PROCESS_EXECUTION, ToolCapability.LOCAL_FILE_READ, ToolCapability.LOCAL_FILE_WRITE, ToolCapability.NETWORK_WRITE}
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/terminal_tool.py",
        rationale="Arbitrary shell command execution.",
    ),
)

# --- R5 (3 tools) ---
_R5_ENTRIES: tuple[ToolPolicyEntry, ...] = (
    ToolPolicyEntry(
        canonical_name="cronjob",
        primary_risk=ToolRiskLevel.R5,
        capabilities=frozenset(
            {
                ToolCapability.SCHEDULING,
                ToolCapability.LOCAL_FILE_READ,
                ToolCapability.LOCAL_FILE_WRITE,
                ToolCapability.ADMINISTRATIVE_ACTION,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/cronjob_tools.py",
        rationale="Creates/modifies scheduled jobs that can spawn arbitrary agent runs.",
    ),
    ToolPolicyEntry(
        canonical_name="discord_admin",
        primary_risk=ToolRiskLevel.R5,
        capabilities=frozenset(
            {
                ToolCapability.NETWORK_WRITE,
                ToolCapability.CREDENTIAL_USE,
                ToolCapability.ADMINISTRATIVE_ACTION,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/discord_tool.py",
        rationale="Discord server admin — bans, kicks, channel creation/deletion.",
    ),
    ToolPolicyEntry(
        canonical_name="ha_call_service",
        primary_risk=ToolRiskLevel.R5,
        capabilities=frozenset(
            {
                ToolCapability.NETWORK_WRITE,
                ToolCapability.CREDENTIAL_USE,
                ToolCapability.REMOTE_STATE_MUTATION,
                ToolCapability.ADMINISTRATIVE_ACTION,
            }
        ),
        permanently_denied=True,
        candidate_allowlisted=False,
        statically_allowed=False,
        source="tools/homeassistant_tool.py",
        rationale="Controls IoT devices — physical device impact.",
    ),
)

# --- Merge into single immutable inventory ---
_TOOL_POLICY_INVENTORY_RAW: dict[str, ToolPolicyEntry] = {}
for _entry in _R0_ENTRIES + _R1_ENTRIES + _R2_ENTRIES + _R3_ENTRIES + _R4_ENTRIES + _R5_ENTRIES:
    _TOOL_POLICY_INVENTORY_RAW[_entry.canonical_name] = _entry

TOOL_POLICY_INVENTORY: Mapping[str, ToolPolicyEntry] = MappingProxyType(_TOOL_POLICY_INVENTORY_RAW)


# ---------------------------------------------------------------------------
# 7. Derived sets — all immutable
# ---------------------------------------------------------------------------

ALL_CANONICAL_TOOLS: frozenset[str] = frozenset(TOOL_POLICY_INVENTORY.keys())

STATIC_DENYLIST: frozenset[str] = frozenset(
    name for name, entry in TOOL_POLICY_INVENTORY.items() if entry.permanently_denied
)

CANDIDATE_ALLOWLIST: frozenset[str] = frozenset(
    name for name, entry in TOOL_POLICY_INVENTORY.items() if entry.candidate_allowlisted
)

STATIC_ALLOWLIST: frozenset[str] = frozenset({"clarify"})

_TOOLS_BY_RISK_RAW: dict[ToolRiskLevel, frozenset[str]] = {}
for _risk in ToolRiskLevel:
    _TOOLS_BY_RISK_RAW[_risk] = frozenset(
        name for name, entry in TOOL_POLICY_INVENTORY.items() if entry.primary_risk is _risk
    )
TOOLS_BY_RISK: Mapping[ToolRiskLevel, frozenset[str]] = MappingProxyType(_TOOLS_BY_RISK_RAW)

# Freeze the maximum-nesting constant used by schema validation.
_SCHEMA_MAX_DEPTH: int = 8


# ---------------------------------------------------------------------------
# 8. Integrity verification — runs once at import time
# ---------------------------------------------------------------------------


def _verify_inventory_integrity() -> None:
    """Pure-memory integrity check.  Raises ``RuntimeError`` on failure.

    Does NOT access Registry, filesystem, database, or network.
    """
    errors: list[str] = []

    # Total count
    total = len(TOOL_POLICY_INVENTORY)
    if total != 71:
        errors.append(f"Inventory count: expected 71, got {total}")

    # Unique names
    names = set(TOOL_POLICY_INVENTORY.keys())
    if len(names) != total:
        errors.append(f"Duplicate canonical names detected: {total - len(names)} duplicates")

    # Empty names
    empty = [n for n in names if not n or n != n.strip()]
    if empty:
        errors.append(f"Empty or padded canonical names: {empty}")

    # Risk counts
    expected_risk: dict[ToolRiskLevel, int] = {
        ToolRiskLevel.R0: 1,
        ToolRiskLevel.R1: 5,
        ToolRiskLevel.R2: 19,
        ToolRiskLevel.R3: 26,
        ToolRiskLevel.R4: 17,
        ToolRiskLevel.R5: 3,
    }
    for risk, expected_count in expected_risk.items():
        actual = len(TOOLS_BY_RISK[risk])
        if actual != expected_count:
            errors.append(f"Risk {risk.value}: expected {expected_count}, got {actual}")

    risk_total = sum(len(v) for v in TOOLS_BY_RISK.values())
    if risk_total != 71:
        errors.append(f"Risk total: expected 71, got {risk_total}")

    # Multiply classified
    name_risk_count: dict[str, int] = {}
    for entry in TOOL_POLICY_INVENTORY.values():
        name_risk_count[entry.canonical_name] = name_risk_count.get(entry.canonical_name, 0) + 1
    multi = {n: c for n, c in name_risk_count.items() if c > 1}
    if multi:
        errors.append(f"Multiply classified tools: {multi}")

    # Denylist
    if len(STATIC_DENYLIST) != 26:
        errors.append(f"STATIC_DENYLIST: expected 26, got {len(STATIC_DENYLIST)}")
    deny_unknown = STATIC_DENYLIST - ALL_CANONICAL_TOOLS
    if deny_unknown:
        errors.append(f"Denylist names not in inventory: {deny_unknown}")

    # Candidate
    if len(CANDIDATE_ALLOWLIST) != 6:
        errors.append(f"CANDIDATE_ALLOWLIST: expected 6, got {len(CANDIDATE_ALLOWLIST)}")
    cand_unknown = CANDIDATE_ALLOWLIST - ALL_CANONICAL_TOOLS
    if cand_unknown:
        errors.append(f"Candidate names not in inventory: {cand_unknown}")

    # Static allowlist must contain exactly {"clarify"} (Phase 1G-04-14)
    if len(STATIC_ALLOWLIST) != 1 or STATIC_ALLOWLIST != frozenset({"clarify"}):
        errors.append(f"STATIC_ALLOWLIST: expected {{'clarify'}}, got {STATIC_ALLOWLIST}")

    # Denylist ⊆ inventory (already checked above)
    # Candidate ⊆ inventory (already checked above)
    # Static Allowlist ⊆ Candidate
    static_not_candidate = STATIC_ALLOWLIST - CANDIDATE_ALLOWLIST
    if static_not_candidate:
        errors.append(f"Static Allowlist not subset of Candidate: {static_not_candidate}")

    # Denylist ∩ Candidate = ∅
    deny_cand_intersect = STATIC_DENYLIST & CANDIDATE_ALLOWLIST
    if deny_cand_intersect:
        errors.append(f"Denylist ∩ Candidate: {deny_cand_intersect}")

    # Denylist ∩ Static Allowlist = ∅
    deny_static_intersect = STATIC_DENYLIST & STATIC_ALLOWLIST
    if deny_static_intersect:
        errors.append(f"Denylist ∩ Static Allowlist: {deny_static_intersect}")

    # Candidate risks must be only R0 or R1
    for name in CANDIDATE_ALLOWLIST:
        entry = TOOL_POLICY_INVENTORY[name]
        if entry.primary_risk not in (ToolRiskLevel.R0, ToolRiskLevel.R1):
            errors.append(f"Candidate {name} has risk {entry.primary_risk.value}, expected R0 or R1")

    # All permanently denied entries must not be statically allowed
    for name in STATIC_DENYLIST:
        entry = TOOL_POLICY_INVENTORY[name]
        if entry.statically_allowed:
            errors.append(f"Denied tool {name} is marked statically_allowed=True")
        if not entry.permanently_denied:
            errors.append(f"Denylist tool {name} has permanently_denied=False in entry")

    # Every inventory entry agrees with derived sets
    for name, entry in TOOL_POLICY_INVENTORY.items():
        if (name in STATIC_DENYLIST) != entry.permanently_denied:
            errors.append(f"Entry/denylist mismatch for {name}")
        if (name in CANDIDATE_ALLOWLIST) != entry.candidate_allowlisted:
            errors.append(f"Entry/candidate mismatch for {name}")
        if (name in STATIC_ALLOWLIST) != entry.statically_allowed:
            errors.append(f"Entry/static-allowlist mismatch for {name}")

    if errors:
        raise RuntimeError(
            "Static Tool Policy integrity check failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


_verify_inventory_integrity()

# Clean up build-time locals — prevent external access to mutable internals.
del _TOOL_POLICY_INVENTORY_RAW, _TOOLS_BY_RISK_RAW
del _R0_ENTRIES, _R1_ENTRIES, _R2_ENTRIES, _R3_ENTRIES, _R4_ENTRIES, _R5_ENTRIES
del _verify_inventory_integrity


# ---------------------------------------------------------------------------
# 9. Query functions — pure, no side effects
# ---------------------------------------------------------------------------


def get_tool_policy(canonical_name: str) -> ToolPolicyEntry | None:
    """Return the policy entry for *canonical_name*, or ``None`` if unknown."""
    return TOOL_POLICY_INVENTORY.get(canonical_name)


def get_all_tool_policies() -> tuple[ToolPolicyEntry, ...]:
    """Return all policy entries as an immutable tuple."""
    return tuple(TOOL_POLICY_INVENTORY.values())


def get_tools_by_risk(risk: ToolRiskLevel) -> tuple[ToolPolicyEntry, ...]:
    """Return all policy entries matching the given risk level."""
    return tuple(e for e in TOOL_POLICY_INVENTORY.values() if e.primary_risk is risk)


def is_permanently_denied(canonical_name: str) -> bool:
    """Return ``True`` if the tool is on the permanent denylist."""
    return canonical_name in STATIC_DENYLIST


def is_candidate_allowlisted(canonical_name: str) -> bool:
    """Return ``True`` if the tool is a candidate for the allowlist.

    Candidate does NOT mean enabled.  Check ``is_statically_allowed()`` for
    actual enablement.
    """
    return canonical_name in CANDIDATE_ALLOWLIST


def is_statically_allowed(canonical_name: str) -> bool:
    """Return ``True`` if the tool is on the static allowlist."""
    return canonical_name in STATIC_ALLOWLIST


def evaluate_static_tool_policy(requested_name: str) -> ToolPolicyDecision:
    """Evaluate the static policy for *requested_name*.

    **Exact match only.**  No case folding, no whitespace stripping, no
    prefix or wildcard matching, no alias resolution.

    Returns a ``ToolPolicyDecision`` with ``allowed=True`` for tools on the
    static allowlist (currently only ``clarify``), ``allowed=False`` otherwise.
    """
    entry = TOOL_POLICY_INVENTORY.get(requested_name)

    if entry is None:
        return ToolPolicyDecision(
            requested_name=requested_name,
            canonical_name=None,
            known=False,
            permanently_denied=False,
            candidate_allowlisted=False,
            statically_allowed=False,
            allowed=False,
            primary_risk=None,
            reason_code=REASON_TOOL_NOT_FOUND,
        )

    if entry.permanently_denied:
        return ToolPolicyDecision(
            requested_name=requested_name,
            canonical_name=entry.canonical_name,
            known=True,
            permanently_denied=True,
            candidate_allowlisted=entry.candidate_allowlisted,
            statically_allowed=False,
            allowed=False,
            primary_risk=entry.primary_risk,
            reason_code=REASON_TOOL_PERMANENTLY_DENIED,
        )

    # Known and on static allowlist → allowed.
    if entry.statically_allowed:
        return ToolPolicyDecision(
            requested_name=requested_name,
            canonical_name=entry.canonical_name,
            known=True,
            permanently_denied=False,
            candidate_allowlisted=entry.candidate_allowlisted,
            statically_allowed=True,
            allowed=True,
            primary_risk=entry.primary_risk,
            reason_code="TOOL_ALLOWED",
        )

    # Known but not on static allowlist → not allowed (default deny).
    return ToolPolicyDecision(
        requested_name=requested_name,
        canonical_name=entry.canonical_name,
        known=True,
        permanently_denied=False,
        candidate_allowlisted=entry.candidate_allowlisted,
        statically_allowed=False,
        allowed=False,
        primary_risk=entry.primary_risk,
        reason_code=REASON_TOOL_NOT_ALLOWED,
    )


# ---------------------------------------------------------------------------
# 10. Schema safety validation — pure function
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolSchemaValidationResult:
    """Result of schema safety validation."""

    valid: bool
    errors: tuple[str, ...]


_FORBIDDEN_SCHEMA_KEYS: frozenset[str] = frozenset(
    {"__proto__", "constructor", "prototype"}
)


def validate_tool_schema_safety(schema: Mapping[str, object]) -> ToolSchemaValidationResult:
    """Validate a tool parameter schema for safety constraints.

    Pure function — does NOT modify the schema, read the Registry, or
    access the filesystem.

    Checks:
      - Root must be ``type: "object"``
      - ``properties`` must be a mapping
      - ``required`` must be a list of strings that exist in ``properties``
      - ``additionalProperties`` must be ``False``
      - No empty property names
      - No forbidden keys (``__proto__``, ``constructor``, ``prototype``)
      - Nesting depth ≤ 8
      - Nested objects must also have ``additionalProperties: false``
    """
    errors: list[str] = []

    # Root type check
    if schema.get("type") != "object":
        errors.append("Root type must be 'object'")

    # Properties check
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        errors.append("'properties' must be an object")
    else:
        for key in properties:
            if not key or not isinstance(key, str):
                errors.append(f"Empty property name found")
            if key in _FORBIDDEN_SCHEMA_KEYS:
                errors.append(f"Forbidden property key: {key}")

    # Required fields check
    required = schema.get("required")
    if required is not None:
        if not isinstance(required, list):
            errors.append("'required' must be an array")
        elif isinstance(properties, dict):
            for field in required:
                if not isinstance(field, str):
                    errors.append(f"Required field must be string: {field!r}")
                elif field not in properties:
                    errors.append(f"Required field '{field}' not in properties")

    # additionalProperties must be false
    if schema.get("additionalProperties") is not False:
        errors.append("'additionalProperties' must be false")

    # Recursive depth + nested object checks
    _check_schema_depth(schema, 0, errors, _SCHEMA_MAX_DEPTH)

    return ToolSchemaValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
    )


def _check_schema_depth(
    node: object,
    depth: int,
    errors: list[str],
    max_depth: int,
) -> None:
    """Recursively validate schema depth and nested object constraints."""
    if not isinstance(node, dict):
        return
    if depth > max_depth:
        errors.append(f"Schema nesting depth exceeds {max_depth}")
        return

    for key, value in node.items():
        if key in _FORBIDDEN_SCHEMA_KEYS:
            errors.append(f"Forbidden key in schema: {key}")
        if isinstance(value, dict):
            if value.get("type") == "object":
                if value.get("additionalProperties") is not False:
                    errors.append(
                        f"Nested object at key '{key}' must have additionalProperties=false"
                    )
            _check_schema_depth(value, depth + 1, errors, max_depth)


# ---------------------------------------------------------------------------
# 11. Argument structure validation — pure function
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolArgumentValidationResult:
    """Result of argument structure validation."""

    valid: bool
    errors: tuple[str, ...]
    payload_bytes: int
    max_depth: int


_FORBIDDEN_ARG_KEYS: frozenset[str] = frozenset(
    {"__proto__", "constructor", "prototype"}
)


def validate_argument_structure(arguments: object) -> ToolArgumentValidationResult:
    """Validate tool call arguments against structural safety limits.

    Pure function — does NOT call tool handlers, check filesystem, or
    access the network.

    Checks:
      - JSON-serializable and serialized size ≤ 32 KiB
      - Nesting depth ≤ 8
      - String values ≤ 4000 characters
      - Array length ≤ 100
      - Object keys must be strings (not forbidden keys)
      - No NaN or Infinity values
      - No non-JSON-serializable objects
    """
    errors: list[str] = []
    payload_bytes = 0
    max_depth = 0

    # JSON serialization check
    try:
        serialized = json.dumps(arguments, ensure_ascii=False)
        payload_bytes = len(serialized.encode("utf-8"))
    except (TypeError, ValueError, OverflowError) as exc:
        errors.append(f"Arguments are not JSON-serializable: {exc}")
        return ToolArgumentValidationResult(
            valid=False,
            errors=tuple(errors),
            payload_bytes=0,
            max_depth=0,
        )

    # Payload size
    if payload_bytes > MAX_ARGUMENT_PAYLOAD_BYTES:
        errors.append(
            f"Payload {payload_bytes} bytes exceeds limit {MAX_ARGUMENT_PAYLOAD_BYTES}"
        )

    # Recursive structure check
    _max_depth_ref = [0]
    _check_argument_structure(arguments, 0, errors, _max_depth_ref)
    max_depth = _max_depth_ref[0]

    return ToolArgumentValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        payload_bytes=payload_bytes,
        max_depth=max_depth,
    )


def _check_argument_structure(
    value: object,
    depth: int,
    errors: list[str],
    max_depth_ref: list[int],
) -> None:
    """Recursively validate argument structure."""
    if depth > max_depth_ref[0]:
        max_depth_ref[0] = depth

    if depth > MAX_ARGUMENT_NESTING_DEPTH:
        errors.append(f"Nesting depth exceeds {MAX_ARGUMENT_NESTING_DEPTH}")
        return

    if isinstance(value, float):
        if math.isnan(value):
            errors.append("NaN is not allowed in arguments")
        if math.isinf(value):
            errors.append("Infinity is not allowed in arguments")
        return

    if isinstance(value, str):
        if len(value) > MAX_ARGUMENT_STRING_LENGTH:
            errors.append(
                f"String length {len(value)} exceeds limit {MAX_ARGUMENT_STRING_LENGTH}"
            )
        return

    if isinstance(value, list):
        if len(value) > MAX_ARGUMENT_ARRAY_LENGTH:
            errors.append(
                f"Array length {len(value)} exceeds limit {MAX_ARGUMENT_ARRAY_LENGTH}"
            )
        for item in value:
            _check_argument_structure(item, depth + 1, errors, max_depth_ref)
        return

    if isinstance(value, dict):
        for key in value:
            if not isinstance(key, str):
                errors.append(f"Object key must be string, got {type(key).__name__}")
            elif key in _FORBIDDEN_ARG_KEYS:
                errors.append(f"Forbidden key in arguments: {key}")
        for v in value.values():
            _check_argument_structure(v, depth + 1, errors, max_depth_ref)
        return

    # bool, int, None are safe at leaf level


# ---------------------------------------------------------------------------
# 12. Policy completeness validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ToolPolicyValidationResult:
    """Result of static policy completeness validation."""

    valid: bool
    errors: tuple[str, ...]
    canonical_count: int
    risk_counts: Mapping[ToolRiskLevel, int]


def validate_static_tool_policy() -> ToolPolicyValidationResult:
    """Validate the static tool policy for completeness and consistency.

    Pure-memory check.  Does NOT access Registry, filesystem, or database.
    """
    errors: list[str] = []
    risk_counts: dict[ToolRiskLevel, int] = {}

    for risk in ToolRiskLevel:
        count = len(TOOLS_BY_RISK[risk])
        risk_counts[risk] = count

    canonical_count = len(TOOL_POLICY_INVENTORY)

    if canonical_count != 71:
        errors.append(f"Expected 71 canonical tools, got {canonical_count}")

    expected: dict[ToolRiskLevel, int] = {
        ToolRiskLevel.R0: 1,
        ToolRiskLevel.R1: 5,
        ToolRiskLevel.R2: 19,
        ToolRiskLevel.R3: 26,
        ToolRiskLevel.R4: 17,
        ToolRiskLevel.R5: 3,
    }
    for risk, exp in expected.items():
        if risk_counts[risk] != exp:
            errors.append(f"Risk {risk.value}: expected {exp}, got {risk_counts[risk]}")

    total = sum(risk_counts.values())
    if total != 71:
        errors.append(f"Risk total: expected 71, got {total}")

    if len(STATIC_DENYLIST) != 26:
        errors.append(f"Denylist: expected 26, got {len(STATIC_DENYLIST)}")

    if len(CANDIDATE_ALLOWLIST) != 6:
        errors.append(f"Candidate: expected 6, got {len(CANDIDATE_ALLOWLIST)}")

    if STATIC_ALLOWLIST != frozenset({"clarify"}):
        errors.append(f"Static Allowlist: expected {{'clarify'}}, got {STATIC_ALLOWLIST}")

    deny_unknown = STATIC_DENYLIST - ALL_CANONICAL_TOOLS
    if deny_unknown:
        errors.append(f"Denylist not subset of inventory: {deny_unknown}")

    cand_unknown = CANDIDATE_ALLOWLIST - ALL_CANONICAL_TOOLS
    if cand_unknown:
        errors.append(f"Candidate not subset of inventory: {cand_unknown}")

    static_unknown = STATIC_ALLOWLIST - CANDIDATE_ALLOWLIST
    if static_unknown:
        errors.append(f"Static Allowlist not subset of Candidate: {static_unknown}")

    deny_cand = STATIC_DENYLIST & CANDIDATE_ALLOWLIST
    if deny_cand:
        errors.append(f"Denylist ∩ Candidate: {deny_cand}")

    deny_static = STATIC_DENYLIST & STATIC_ALLOWLIST
    if deny_static:
        errors.append(f"Denylist ∩ Static Allowlist: {deny_static}")

    for name in CANDIDATE_ALLOWLIST:
        entry = TOOL_POLICY_INVENTORY[name]
        if entry.primary_risk not in (ToolRiskLevel.R0, ToolRiskLevel.R1):
            errors.append(f"Candidate {name} has risk {entry.primary_risk.value}")

    for name in STATIC_DENYLIST:
        entry = TOOL_POLICY_INVENTORY[name]
        if entry.statically_allowed:
            errors.append(f"Denied tool {name} is statically_allowed")

    return ToolPolicyValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        canonical_count=canonical_count,
        risk_counts=MappingProxyType(risk_counts),
    )
