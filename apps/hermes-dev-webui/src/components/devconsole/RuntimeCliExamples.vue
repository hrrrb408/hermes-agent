<script setup lang="ts">
/**
 * Runtime Governance CLI examples (Phase 3J).
 *
 * Read-only, text-only documentation for the developer-facing
 * `hermes dev-runtime` CLI that runs OUTSIDE the WebUI. The WebUI renders these
 * as plain text inside <code> blocks — it never executes a command, never
 * spawns a shell, never copies to a clipboard action that runs anything, and
 * never writes the example to a file. There are no buttons here.
 */
import type { RuntimeCliExample } from '@/types/api/runtimeGovernance'

defineProps<{
  examples: readonly RuntimeCliExample[]
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="runtime-cli-examples">
    <h3>CLI command examples (run outside the WebUI)</h3>
    <p class="rtgov-muted">
      These commands drive the Phase 3I runtime governance CLI from a terminal.
      They are shown here for reference only — the WebUI is read-only and
      provides no Run / Execute / Batch / Approve / Authorize control.
    </p>
    <ul class="rtgov-cli" data-testid="runtime-cli-list">
      <li v-for="ex in examples" :key="ex.command" class="rtgov-cli__item">
        <code class="rtgov-cli__code" data-cli-command>{{ ex.command }}</code>
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
.rtgov-cli__code {
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
</style>
