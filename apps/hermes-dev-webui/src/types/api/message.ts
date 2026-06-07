/**
 * TypeScript types for the Dev API message endpoints.
 *
 * Matches the frozen OpenAPI contract in docs/webui/openapi/dev-web-api-v1.yaml.
 */

// ── Message Content ──

/** Text message content. */
export interface TextContent {
  readonly type: 'text'
  readonly text: string
  readonly truncated?: boolean
}

/** Empty message content. */
export interface EmptyContent {
  readonly type: 'empty'
}

/** Unsupported message content placeholder. */
export interface UnsupportedContent {
  readonly type: 'unsupported'
}

/** Discriminated union of all content types. */
export type MessageContent = TextContent | EmptyContent | UnsupportedContent

// ── Tool Calls ──

/** A function call within a tool call. */
export interface ToolCallFunction {
  readonly name: string
  readonly arguments: string
}

/** A single tool call in an assistant message. */
export interface ToolCall {
  readonly id: string
  readonly type: 'function'
  readonly function: ToolCallFunction
}

// ── Message ──

/** Message role type. */
export type MessageRole = 'user' | 'assistant' | 'tool' | 'system' | 'unknown'

/** A single message in the messages response. */
export interface SessionMessage {
  readonly id: number
  readonly role: MessageRole
  readonly content: MessageContent
  readonly timestamp: string | null
  readonly tokenCount?: number | null
  readonly finishReason?: string | null
  readonly toolCalls?: ToolCall[] | null
  readonly toolCallId?: string | null
  readonly toolName?: string | null
}

// ── Pagination ──

/** Pagination metadata for message list. */
export interface MessagePage {
  readonly offset: number
  readonly limit: number
  readonly total: number
  readonly hasMore: boolean
  readonly messagesBefore?: number | null
  readonly messagesAfter?: number | null
}

// ── Response ──

/** Response data for GET /sessions/{sessionId}/messages. */
export interface MessageListData {
  readonly items: readonly SessionMessage[]
  readonly page: MessagePage
}

// ── Query Parameters ──

/** Parameters for GET /sessions/{sessionId}/messages. */
export interface MessageListParams {
  readonly limit?: number
  readonly offset?: number
  readonly before?: number
  readonly after?: number
}
