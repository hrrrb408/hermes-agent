<script setup lang="ts">
/**
 * Runtime Governance CLI examples (Phase 3J).
 *
 * Read-only, text-only documentation for the developer-facing
 * `hermes dev-runtime` CLI that runs OUTSIDE the WebUI. The WebUI renders these
 * as plain text inside <code> blocks. The only interactive control is a
 * harmless **Copy** button that writes the command string to the clipboard — it
 * never executes a command, never spawns a shell, never calls the backend,
 * never reads or writes a file, and never touches the runtime. If the
 * clipboard API is unavailable or rejects, the button shows a harmless
 * "Unavailable" state and still executes nothing.
 */
import { reactive } from 'vue'
import { Copy, Check } from '@lucide/vue'
import type { RuntimeCliExample } from '@/types/api/runtimeGovernance'

defineProps<{
  examples: readonly RuntimeCliExample[]
}>()

/** Per-command copy state: 'idle' | 'copied' | 'unavailable'. Harmless UI-only. */
const copyState = reactive<Record<string, 'copied' | 'unavailable'>>({})

async function copyCommand(command: string): Promise<void> {
  // Clipboard is the ONLY side effect, and it is a local UI affordance — never
  // an execution, network, or file operation. Guard for environments without it.
  const clipboard = globalThis.navigator?.clipboard
  if (!clipboard || typeof clipboard.writeText !== 'function') {
    copyState[command] = 'unavailable'
    return
  }
  try {
    await clipboard.writeText(command)
    copyState[command] = 'copied'
  } catch {
    // A clipboard rejection is harmless — never fall back to execution.
    copyState[command] = 'unavailable'
  }
}
</script>

<template>
  <div class="devconsole-card" data-testid="runtime-cli-examples">
    <h2>CLI command examples (run outside the WebUI)</h2>
    <p class="rtgov-muted">
      These commands drive the Phase 3I runtime governance CLI from a terminal.
      They are shown here for reference only — the WebUI is read-only and
      provides no Run / Execute / Batch / Approve / Authorize control. The Copy
      button copies the command text to the clipboard; it does not execute it.
    </p>
    <ul class="rtgov-cli" data-testid="runtime-cli-list">
      <li v-for="(ex, index) in examples" :key="ex.command" class="rtgov-cli__item">
        <div class="rtgov-cli__row">
          <code class="rtgov-cli__code" data-cli-command>{{ ex.command }}</code>
          <button
            type="button"
            class="rtgov-cli__copy"
            :aria-label="`Copy command example ${index + 1}`"
            :data-testid="`runtime-cli-copy-${ex.command}`"
            :data-copy-state="copyState[ex.command] ?? 'idle'"
            @click="copyCommand(ex.command)"
          >
            <Check v-if="copyState[ex.command] === 'copied'" :size="13" aria-hidden="true" />
            <Copy v-else :size="13" aria-hidden="true" />
            <span>{{ copyState[ex.command] === 'copied' ? 'Copied' : copyState[ex.command] === 'unavailable' ? 'Unavailable' : 'Copy' }}</span>
          </button>
        </div>
        <span class="rtgov-cli__summary">{{ ex.summary }}</span>
        <span v-if="ex.aliases.length" class="rtgov-cli__aliases">
          alias<span v-if="ex.aliases.length > 1">es</span>:
          <code v-for="a in ex.aliases" :key="a">{{ a }}</code>
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.rtgov-muted {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.rtgov-cli {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.rtgov-cli__item {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.rtgov-cli__row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}
.rtgov-cli__code {
  flex: 1 1 240px;
  display: block;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  word-break: break-all;
  white-space: pre-wrap;
}
.rtgov-cli__summary {
  display: block;
  margin-top: var(--space-1, 4px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.rtgov-cli__aliases {
  display: inline-block;
  margin-top: var(--space-1, 4px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
.rtgov-cli__aliases code {
  margin-left: var(--space-1, 4px);
  font-family: var(--font-mono, ui-monospace, monospace);
}
.rtgov-cli__copy {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
  white-space: nowrap;
}
.rtgov-cli__copy:hover {
  border-color: var(--color-accent, #6f8cff);
}
.rtgov-cli__copy:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
</style>
