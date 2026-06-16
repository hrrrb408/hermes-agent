# Phase 3B Provider Config Model

| Field | Value |
|-------|-------|
| Phase | 3B |
| Status | Implemented |
| Module | `hermes_cli/dev_web_provider_config.py` |

## Env surface (read only; never the key value)

| Env | Default | Clamp |
|-----|---------|-------|
| `HERMES_PROVIDER_MODE` | `disabled` | disabled \| fake \| real |
| `HERMES_PROVIDER_API_ENABLED` | `0` (off) | `0` \| `1` |
| `HERMES_PROVIDER_NAME` | `openai_compatible` | known names; only `openai_compatible` is implemented |
| `HERMES_PROVIDER_BASE_URL` | empty | https host allowlist only |
| `HERMES_PROVIDER_MODEL` | empty | model allowlist |
| `HERMES_PROVIDER_TIMEOUT_SECONDS` | `20` | `[1, 60]` |
| `HERMES_PROVIDER_MAX_RETRIES` | `2` | `[0, 4]` |
| `HERMES_PROVIDER_DAILY_BUDGET_CENTS` | `100` | `[0, 500]` |

## Allowlists

- **Base-URL hosts:** `api.openai.com`, `api.z.ai`, `open.bigmodel.cn`. https
  only; the host is reduced to the allowlisted name (never a secret-bearing URL).
- **Models:** `gpt-4o-mini`, `gpt-4o`, `glm-4-flash`, `glm-4`.
- **API-key env vars** (presence only): `HERMES_PROVIDER_API_KEY`,
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`, `ZAI_API_KEY`,
  `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`.

## Value-free projection

`ProviderRealConfig.to_safe_dict()` carries only:
`apiKeySource: "env"`, `apiKeyPresent: bool`, `apiKeySourceDetail:
"env_present" | "env_missing"`, the allowlisted host, the model name, the caps.
It **never** carries the key value, an Authorization header, a raw token, or a
full tokenHash.

## Rate / budget caps (frozen)

- per-minute request cap: 20
- daily request cap: 200
- daily token cap: 500,000
- daily budget cap: from `HERMES_PROVIDER_DAILY_BUDGET_CENTS` (clamped ≤ 500)
- per-request max tokens: `[1, 4096]`
