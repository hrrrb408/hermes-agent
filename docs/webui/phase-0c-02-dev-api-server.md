# Hermes Dev WebUI Phase 0C-02
## Dev-only API Server Skeleton

**Status:** Completed
**Phase:** 0C-02
**API Version:** v1
**Implementation commit:** `ccf8320c1`

---

## 1. 目标

- 建立独立 Dev-only FastAPI 服务
- 与生产 Gateway 和 Dashboard 完全隔离
- 只绑定本机 `127.0.0.1`
- 只允许开发 HERMES_HOME
- 建立统一 Request ID
- 建立统一错误模型
- 建立严格 CORS
- 实现两个只读状态接口
- 为 Phase 0C-03～0C-06 提供稳定运行基线

---

## 2. 架构

```
Dev WebUI (127.0.0.1:5180)
       │ HTTP GET / POST
       ▼
Dev Web API (127.0.0.1:5181)
       │
   ┌───┴───────────────────┐
   │  FastAPI Application   │
   │  ┌─────────────────┐  │
   │  │ Request ID MW   │  │
   │  ├─────────────────┤  │
   │  │ CORS Middleware │  │
   │  ├─────────────────┤  │
   │  │ Error Handlers  │  │
   │  ├─────────────────┤  │
   │  │ Routes          │  │
   │  │  GET /status    │  │
   │  │  GET /files/... │  │
   │  └─────────────────┘  │
   └───────────────────────┘
       │
  No connections to:
  ✕ Agent Runtime
  ✕ SessionDB
  ✕ Memory Router
  ✕ LLM
  ✕ Tool Execution
  ✕ Gateway
```

---

## 3. 运行方式

### 正式命令

```bash
HERMES_HOME=/Users/huangruibang/Code/hermes-home-dev \
python -m hermes_cli.main dev-webui-api
```

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--host` | `127.0.0.1` | 仅允许 `127.0.0.1` |
| `--port` | `5181` | 绑定端口 |

### 帮助

```bash
python -m hermes_cli.main dev-webui-api --help
```

---

## 4. 固定配置

| Item | Value |
|------|-------|
| Host | `127.0.0.1` |
| Port | `5181` |
| API Prefix | `/api/dev/v1` |
| WebUI Origin | `http://127.0.0.1:5180` |
| Mode | foreground |
| Read-only | true |

### 环境变量

| Variable | Default | Purpose |
|----------|---------|---------|
| `HERMES_HOME` | (required) | 开发 Hermes Home 路径 |
| `HERMES_DEV_WEB_API_HOST` | `127.0.0.1` | 覆盖 host（仍仅允许 127.0.0.1） |
| `HERMES_DEV_WEB_API_PORT` | `5181` | 覆盖 port |

---

## 5. 环境隔离

- 必须设置 `HERMES_HOME`
- 路径必须存在且为目录
- 不得等于 `~/.hermes`
- 不得位于 `~/.hermes` 下
- 符号链接绕过会被拒绝（resolve 后检查）
- 不安全配置 fail closed（拒绝启动，非零退出码）
- 不会回退到生产目录

---

## 6. 已实现 Endpoint

### GET /api/dev/v1/status

系统状态、环境隔离校验、服务可用性。

响应示例（已脱敏）：

```json
{
  "data": {
    "environment": "development",
    "apiVersion": "v1",
    "status": "ok",
    "readOnly": true,
    "bind": {"host": "127.0.0.1", "port": 5181},
    "isolation": {
      "passed": true,
      "usesDevelopmentHome": true,
      "productionHomeUntouched": true
    },
    "services": {
      "api": {"available": true, "readOnly": true},
      "sessions": {"available": false, "readOnly": true, "phase": "0C-03"},
      "memory": {"available": false, "readOnly": true, "phase": "0C-05"},
      "agent": {"available": false, "readOnly": true, "phase": "0C-05"},
      "files": {"available": false, "readOnly": true}
    }
  },
  "meta": {"requestId": "...", "timestamp": "2026-06-07T12:51:56Z"}
}
```

### GET /api/dev/v1/files/status

文件浏览可用性状态（当前不可用）。

响应示例：

```json
{
  "data": {
    "available": false,
    "readOnly": true,
    "browseEnabled": false,
    "uploadEnabled": false,
    "downloadEnabled": false,
    "deleteEnabled": false,
    "reason": "Files integration is not available in Phase 0C."
  },
  "meta": {"requestId": "...", "timestamp": "..."}
}
```

---

## 7. 未实现 Endpoint

以下接口返回统一 404，不返回 Mock 数据：

| Endpoint | Frozen Phase |
|----------|-------------|
| `GET /sessions` | 0C-03 |
| `GET /sessions/{id}` | 0C-03 |
| `GET /sessions/{id}/messages` | 0C-04 |
| `POST /context/preview` | 0C-05 |
| `GET /memory/status` | 0C-05 |
| `GET /memory/categories` | 0C-05 |
| `GET /memory/items` | 0C-05 |
| `GET /memory/items/{id}` | 0C-05 |
| `GET /agent/status` | 0C-05 |

`/reviews` 已不属于冻结 Phase 0C API（在 Phase 0C-01 收口时移除）。

**静态冻结契约定义 11 个 endpoint，Phase 0C-02 运行时仅注册 2 个已实现 endpoint。**

---

## 8. Request ID

| Property | Value |
|----------|-------|
| Header | `X-Request-ID` |
| 生成方式 | UUID4 hex（32 字符） |
| 最大长度 | 64 字符 |
| 非法值处理 | 含换行/控制字符/超长 → 生成新 ID，不回显原始值 |
| 响应 Header | 所有响应包含 `X-Request-ID` |
| 响应 Body | `meta.requestId` 字段 |
| 错误响应 | 404/405/422/500 均包含 |

---

## 9. 错误模型

统一格式：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Resource was not found.",
    "details": null
  },
  "requestId": "e622b29a3fc64a7280ce71b5293b55c8",
  "timestamp": "2026-06-07T12:55:31Z"
}
```

### 错误码

| Code | HTTP | Usage |
|------|------|-------|
| `BAD_REQUEST` | 400 | 参数格式错误 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | HTTP 方法不允许 |
| `VALIDATION_ERROR` | 422 | 参数校验失败 |
| `UNSAFE_ENVIRONMENT` | 500 | 环境隔离失败 |
| `DEV_API_CONFIGURATION_ERROR` | 500 | 配置错误 |
| `SERVICE_UNAVAILABLE` | 503 | 后端不可用 |
| `INTERNAL_ERROR` | 500 | 未预期错误 |

### 不会暴露

- Python traceback
- 本机绝对路径
- SQL 语句
- API Key / Secret / Token / Cookie
- 内部异常对象
- 环境变量

---

## 10. CORS

### 允许

| Item | Value |
|------|-------|
| Origin | `http://127.0.0.1:5180` |
| Methods | `GET`, `POST`, `OPTIONS` |
| Headers | `Content-Type`, `X-Request-ID` |
| Expose | `X-Request-ID` |
| Credentials | `false` |

### 拒绝

- `*`（通配符）
- `http://localhost:5180`
- `http://127.0.0.1:5186`
- `http://127.0.0.1:3000`
- `https://example.com`
- `null`

---

## 11. Files Status

- 当前不可用（`available=false`）
- 不支持 `path` 参数
- 不支持浏览、上传、下载、删除
- 不访问任意文件系统
- 不暴露本机目录结构

---

## 12. 测试

| Suite | Count | Result |
|-------|-------|--------|
| Dev Web API tests | 100 | 100 passed, 0 failed |
| Python compileall | — | Pass |
| Ruff check | — | Pass |
| Frontend lint | — | Pass |
| Frontend type-check | — | Pass |
| Frontend tests | 129 | 129 passed |
| Frontend build | 1806 modules | Pass |
| Static OpenAPI (frozen) | 11 paths, 48 schemas | Valid |
| Runtime OpenAPI | 2 paths | Matches implementation |
| memory-check | — | PASS |
| dev-check | — | WARN (5 pre-existing untracked dirs) |
| Formal CLI Smoke Test | Port 5181 | Pass |

### Smoke Test 验证项

- ✅ 正式 CLI 启动（`python -m hermes_cli.main dev-webui-api`）
- ✅ 监听 `127.0.0.1:5181`（仅 IPv4 loopback）
- ✅ `GET /status` → 200, 正确 JSON
- ✅ `GET /files/status` → 200, available=false
- ✅ 客户端 Request ID 正确回显
- ✅ CORS 允许 `http://127.0.0.1:5180`
- ✅ CORS 拒绝 `example.com`, `localhost:5180`, `127.0.0.1:5186`
- ✅ 未实现接口返回 404 + 统一错误模型
- ✅ 错误方法返回 405 + 统一错误模型
- ✅ 不安全 host `0.0.0.0` 被拒绝（exit code 1）
- ✅ 服务停止后 5181 无监听，无残留进程

---

## 13. 非目标

- Session / Message 接入
- Memory / Context Preview 接入
- Agent Status 接入
- LLM 调用
- Tool 执行
- SSE / WebSocket
- 文件浏览/上传/下载
- Gateway 集成
- Dashboard 集成
- Review Queue 接口

---

## 14. 后续阶段

**Phase 0C-03：Session List and Detail Read-only Integration**

输入：
- Phase 0C-02 API Skeleton（commit `ccf8320c1`）
- Phase 0C-01 frozen contract
- `SessionDB(read_only=True)` from `hermes_state.py`
- Session DTO whitelist from Phase 0C-01 audit

---

## 15. 新增文件

| File | Purpose |
|------|---------|
| `hermes_cli/dev_web_config.py` | 配置对象、环境校验、host/port 验证 |
| `hermes_cli/dev_web_schemas.py` | 响应 schema、Request ID 生成/清理 |
| `hermes_cli/dev_web_errors.py` | 统一错误模型、FastAPI 异常处理器 |
| `hermes_cli/dev_web_middleware.py` | Request ID 中间件 |
| `hermes_cli/dev_web_api.py` | FastAPI App Factory + 2 个端点 |
| `tests/test_dev_web_api.py` | 100 个测试 |
| `hermes_cli/main.py` | 添加 `cmd_dev_webui_api` 函数和 CLI 子命令 |
