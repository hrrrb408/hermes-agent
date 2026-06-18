# Phase 3D — Final Threat Model Summary

| Field | Value |
|-------|-------|
| Phase | 3D (Planning Closeout) |
| Title | Plugin Runtime — Final Threat Model Summary |
| Status | Frozen |
| Date | 2026-06-18 |
| Summary ID | `PHASE-3D-FINAL-THREAT-001` |

> Final summary of the 23 plugin-runtime threats frozen in planning. Full detail
> lives in [phase-3d-threat-model.md](phase-3d-threat-model.md). Every threat
> resolves to **NO-GO** in planning; the future runtime is descriptor-only.

## 1. Threat register

| Threat | Title | Category | Stop condition | Review |
|--------|-------|----------|----------------|--------|
| PLUG-THREAT-01 | Dynamic import arbitrary code execution | dynamic / external code | any `importlib` / `__import__` / path-load path | NO-GO |
| PLUG-THREAT-02 | Local plugin directory traversal | dynamic / external code | any local plugin dir read | NO-GO |
| PLUG-THREAT-03 | Remote registry supply-chain attack | remote supply-chain | any remote registry / fetch | NO-GO |
| PLUG-THREAT-04 | Marketplace malicious plugin | remote supply-chain | any marketplace path | NO-GO |
| PLUG-THREAT-05 | Provider-generated plugin injection | untrusted-input exec | provider mutates descriptor set | NO-GO |
| PLUG-THREAT-06 | LLM-generated tool auto-install | untrusted-input exec | any auto-install of LLM tool | NO-GO |
| PLUG-THREAT-07 | Shell command execution | shell / db / production | any shell invocation | NO-GO |
| PLUG-THREAT-08 | Database mutation | shell / db / production | any DB mutation | NO-GO |
| PLUG-THREAT-09 | External HTTP exfiltration | shell / db / production | any outbound HTTP from a plugin path | NO-GO |
| PLUG-THREAT-10 | Production operation escalation | production escalation | any production operation | NO-GO |
| PLUG-THREAT-11 | Capability permission bypass | permission / gate bypass | descriptor elevates its class | NO-GO |
| PLUG-THREAT-12 | Tool policy bypass | permission / gate bypass | plugin skips dry-run / confirmation / audit | NO-GO |
| PLUG-THREAT-13 | Provider live gate bypass | permission / gate bypass | plugin triggers live without gate | NO-GO |
| PLUG-THREAT-14 | Workflow approval bypass | permission / gate bypass | plugin auto-advances / writes workflow | NO-GO |
| PLUG-THREAT-15 | Audit bypass | leak / audit | unaudited action / audit fails open | NO-GO |
| PLUG-THREAT-16 | Secret leak | leak / audit | secret surfaced | NO-GO |
| PLUG-THREAT-17 | Callable repr leak | leak / audit | callable / import path surfaced | NO-GO |
| PLUG-THREAT-18 | Production path leak | leak / audit | production path surfaced | NO-GO |
| PLUG-THREAT-19 | Route governance drift | governance / artifact | new HTTP / Tool-write / Provider route | NO-GO |
| PLUG-THREAT-20 | Runtime artifact commit | governance / artifact | runtime store / JSONL committed | NO-GO |
| PLUG-THREAT-21 | `.claude/` commit | governance / artifact | `.claude/` staged | NO-GO |
| PLUG-THREAT-22 | `~/.hermes` access | production access | plugin reaches `~/.hermes` | NO-GO |
| PLUG-THREAT-23 | Production `state.db` access | production access | plugin reaches production state | NO-GO |

## 2. Planned mitigations (summary)

- **Dynamic / external code (01–06, 09):** descriptor-only data; no code pointer;
  forbidden `pythonImportPath` / `callable` / `shellCommand` / `externalUrl` /
  `downloadUrl` / `dynamicModule` / `localPath` / `remoteUrl`; AST no-dynamic-loading
  scan; audit `plugin_no_dynamic_loading_checked`.
- **Shell / DB / production (07, 08, 10):** forbid `shellCommand` / `sqlStatement`
  / `productionPath`; reject `subprocess` / DB-DML / production paths.
- **Permission / gate bypass (11–14):** descriptors inherit the bound capability's
  permission class (no escalation); no new execution path; provider live gate and
  workflow approval stay separate.
- **Leak / audit (15–18):** recursive forbidden-field scan + scalar type guard +
  safe read-model allowlist + defensive re-redaction; mandatory fail-closed audit.
- **Governance / artifact / production access (19–23):** no new route; runtime data
  gitignored; `.claude/` never staged; `enforce_dev_environment()` allowlist.

## 3. Frozen posture

```
All dynamic execution threats remain NO-GO.
All remote supply-chain threats remain NO-GO.
All production escalation threats remain NO-GO.
All secret/callable/path leak threats require no-leak gates.
```

## 4. Cross-references

- [Phase 3D threat model (full)](phase-3d-threat-model.md)
- [Final security boundary](phase-3d-final-security-boundary.md)
- [Risk closure](phase-3d-risk-closure.md)
