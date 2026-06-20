<script setup lang="ts">
/**
 * Runtime Governance boundary banner (Phase 3J).
 *
 * Surfaces the frozen, read-only authorization boundary for the dev-only
 * descriptor-backed fixture runtime. Every line is an explicit NO-GO /
 * read-only / dev-only / fixture-only / no-production label (non-color
 * identification). The banner is informational only — it grants nothing,
 * toggles nothing, and performs no action.
 */
import { Ban, Lock, ShieldAlert, ShieldX } from '@lucide/vue'
import type { Component } from 'vue'
import type { RuntimeAuthorizationVerdict } from '@/types/api/runtimeGovernance'

defineProps<{
  verdicts: readonly RuntimeAuthorizationVerdict[]
}>()

interface StaticRow {
  readonly icon: Component
  readonly label: string
}

const STATIC_ROWS: readonly StaticRow[] = [
  { icon: Lock, label: 'DEV-ONLY — local fixture runtime' },
  { icon: Lock, label: 'READ-ONLY WebUI surface — no execution from the browser' },
  { icon: Lock, label: 'FIXTURE-ONLY — reviewed-fixture descriptors only' },
  { icon: Ban, label: 'NO real plugin runtime' },
  { icon: Ban, label: 'NO arbitrary plugin loading' },
  { icon: Ban, label: 'NO local plugin directory loading' },
  { icon: Ban, label: 'NO remote registry / marketplace / external plugin fetch' },
  { icon: Ban, label: 'NO external network' },
  { icon: Ban, label: 'NO real API key read' },
  { icon: Ban, label: 'NO new route — backend route counts unchanged' },
  { icon: Ban, label: 'NO production rollout' },
]
</script>

<template>
  <aside
    class="rtgov-banner"
    role="status"
    aria-live="polite"
    data-testid="runtime-boundary-banner"
  >
    <header class="rtgov-banner__header">
      <ShieldAlert :size="16" aria-hidden="true" />
      <h3>Runtime Governance — dev-only, read-only, fixture-only</h3>
    </header>
    <p class="rtgov-banner__note">
      This is a <strong>read-only projection</strong> of the Phase 3I dev-only
      descriptor-backed fixture runtime. It displays the reviewed-fixture
      descriptor registry, the registry→runtime binding, the P0 evidence
      summary, the frozen no-side-effect surface, and CLI examples. It does
      <strong>not</strong> execute a runtime, does not load a plugin, does not
      authorize production, and does not add a backend route.
    </p>
    <ul class="rtgov-banner__list">
      <li v-for="row in STATIC_ROWS" :key="row.label">
        <component :is="row.icon" :size="13" aria-hidden="true" />
        <span>{{ row.label }}</span>
      </li>
    </ul>
    <div class="rtgov-banner__verdicts" data-testid="runtime-boundary-verdicts">
      <div
        v-for="v in verdicts"
        :key="v.key"
        class="rtgov-banner__verdict"
        :data-verdict-key="v.key"
      >
        <ShieldX :size="12" aria-hidden="true" />
        <span class="rtgov-banner__verdict-label">{{ v.label }}</span>
        <span class="rtgov-banner__verdict-value" :data-verdict="v.verdict">{{ v.verdict }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.rtgov-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-md, 8px);
  background: var(--color-surface-raised, #16161c);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  margin-bottom: var(--space-4, 16px);
}
.rtgov-banner__header {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.rtgov-banner__header h3 {
  margin: 0;
  font-size: var(--font-size-md, 14px);
}
.rtgov-banner__note {
  margin: 0 0 var(--space-3, 12px);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.rtgov-banner__list {
  list-style: none;
  margin: 0 0 var(--space-3, 12px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.rtgov-banner__list li {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.rtgov-banner__verdicts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
  border-top: 1px solid var(--color-border, #2a2a33);
  padding-top: var(--space-2, 8px);
}
.rtgov-banner__verdict {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-banner__verdict-label {
  color: var(--color-text-muted, #8a8a94);
}
.rtgov-banner__verdict-value {
  margin-left: auto;
  font-weight: 600;
  color: var(--color-danger, #e0566a);
}
</style>
