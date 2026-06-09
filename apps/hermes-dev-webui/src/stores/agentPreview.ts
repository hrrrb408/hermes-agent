/**
 * Agent Preview store for the Dev WebUI.
 *
 * Manages state for Prompt Preview and Run Dry-Run forms,
 * including loading, error, result, and request race handling.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { previewAgentPrompt, dryRunAgent } from '@/api/agent'
import { isDevApiError } from '@/api/client'

import type {
  AgentPreviewResult,
  AgentPromptPreviewRequest,
  AgentRunDryRunRequest,
} from '@/types/api/agent'

export type PreviewMode = 'prompt' | 'dryRun'
export type PreviewState = 'idle' | 'loading' | 'success' | 'error'

export const useAgentPreviewStore = defineStore('agent-preview', () => {
  // ── State ──

  const activeMode = ref<PreviewMode>('prompt')
  const status = ref<PreviewState>('idle')
  const error = ref('')
  const result = ref<AgentPreviewResult | null>(null)
  const requestId = ref('')

  // ── Form defaults ──

  const promptForm = ref({
    sessionId: '',
    message: '',
    includeHistory: true,
    historyLimit: 20,
    includeMemoryContext: true,
    memoryQuery: '',
    maxCategories: 5,
    maxMemories: 10,
    includeSystemPreview: false,
    includeToolMetadata: true,
    modelOverride: '',
    temperature: null as number | null,
    maxOutputTokens: null as number | null,
  })

  const dryRunForm = ref({
    sessionId: '',
    message: '',
    includeHistory: true,
    historyLimit: 20,
    includeMemoryContext: true,
    memoryQuery: '',
    toolsRequested: false,
    streamRequested: false,
    autoMemoryRequested: false,
    modelOverride: '',
    temperature: null as number | null,
    maxOutputTokens: null as number | null,
  })

  // ── Abort control ──

  let abortController: AbortController | null = null

  // ── Computed ──

  const isLoading = computed(() => status.value === 'loading')
  const isSuccess = computed(() => status.value === 'success')
  const hasResult = computed(() => result.value !== null)

  // ── Helpers ──

  function handleError(err: unknown): string {
    if (isDevApiError(err)) {
      if (err.code === 'REQUEST_CANCELLED') return ''
      return err.message
    }
    return 'An unexpected error occurred.'
  }

  // ── Actions ──

  async function previewPrompt(): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    status.value = 'loading'
    error.value = ''
    result.value = null

    const form = promptForm.value
    const message = form.message.trim()
    if (!message) {
      status.value = 'idle'
      error.value = 'Message is required.'
      return
    }

    const payload: AgentPromptPreviewRequest = {
      message,
      sessionId: form.sessionId.trim() || undefined,
      options: {
        includeHistory: form.includeHistory,
        historyLimit: form.historyLimit,
        includeMemoryContext: form.includeMemoryContext,
        memoryQuery: form.memoryQuery.trim() || undefined,
        maxCategories: form.maxCategories,
        maxMemories: form.maxMemories,
        includeSystemPreview: form.includeSystemPreview,
        includeToolMetadata: form.includeToolMetadata,
      },
      overrides: {
        model: form.modelOverride.trim() || null,
        temperature: form.temperature,
        maxOutputTokens: form.maxOutputTokens,
      },
    }

    try {
      const response = await previewAgentPrompt(payload, abortController.signal)
      result.value = response.data
      requestId.value = response.meta.requestId
      status.value = 'success'
    } catch (err: unknown) {
      const msg = handleError(err)
      if (!msg) return // cancelled
      error.value = msg
      status.value = 'error'
    }
  }

  async function previewRun(): Promise<void> {
    abortController?.abort()
    abortController = new AbortController()
    status.value = 'loading'
    error.value = ''
    result.value = null

    const form = dryRunForm.value
    const message = form.message.trim()
    if (!message) {
      status.value = 'idle'
      error.value = 'Message is required.'
      return
    }

    const payload: AgentRunDryRunRequest = {
      message,
      sessionId: form.sessionId.trim() || undefined,
      options: {
        includeHistory: form.includeHistory,
        historyLimit: form.historyLimit,
        includeMemoryContext: form.includeMemoryContext,
        memoryQuery: form.memoryQuery.trim() || undefined,
        toolsRequested: form.toolsRequested,
        streamRequested: form.streamRequested,
        autoMemoryRequested: form.autoMemoryRequested,
      },
      overrides: {
        model: form.modelOverride.trim() || null,
        temperature: form.temperature,
        maxOutputTokens: form.maxOutputTokens,
      },
    }

    try {
      const response = await dryRunAgent(payload, abortController.signal)
      result.value = response.data
      requestId.value = response.meta.requestId
      status.value = 'success'
    } catch (err: unknown) {
      const msg = handleError(err)
      if (!msg) return // cancelled
      error.value = msg
      status.value = 'error'
    }
  }

  function setMode(mode: PreviewMode): void {
    activeMode.value = mode
    // Clear previous result when switching modes
    result.value = null
    status.value = 'idle'
    error.value = ''
  }

  function retry(): void {
    if (activeMode.value === 'prompt') {
      previewPrompt()
    } else {
      previewRun()
    }
  }

  function clear(): void {
    abortController?.abort()
    status.value = 'idle'
    error.value = ''
    result.value = null
    requestId.value = ''
  }

  function resetForms(): void {
    promptForm.value = {
      sessionId: '',
      message: '',
      includeHistory: true,
      historyLimit: 20,
      includeMemoryContext: true,
      memoryQuery: '',
      maxCategories: 5,
      maxMemories: 10,
      includeSystemPreview: false,
      includeToolMetadata: true,
      modelOverride: '',
      temperature: null,
      maxOutputTokens: null,
    }
    dryRunForm.value = {
      sessionId: '',
      message: '',
      includeHistory: true,
      historyLimit: 20,
      includeMemoryContext: true,
      memoryQuery: '',
      toolsRequested: false,
      streamRequested: false,
      autoMemoryRequested: false,
      modelOverride: '',
      temperature: null,
      maxOutputTokens: null,
    }
  }

  return {
    activeMode,
    status,
    error,
    result,
    requestId,
    promptForm,
    dryRunForm,
    isLoading,
    isSuccess,
    hasResult,
    previewPrompt,
    previewRun,
    setMode,
    retry,
    clear,
    resetForms,
  }
})
