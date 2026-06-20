<script setup lang="ts">
/**
 * Human Review Governance gate detail (Phase 3K).
 *
 * Read-only projection of a selected P0 gate (no approval, no execution).
 * Renders two static states:
 *   - gate   : a known gate (resolved=false, approved=false, NO-GO)
 *   - empty  : no gate selected
 *
 * Every field is read-only text. There is NO Approve / Reject / Authorize / Sign
 * off / Resolve / Override / Mark reviewed / Mark approved control. The only
 * interactive affordance is a harmless **Copy** button that copies the gate id to
 * the clipboard — it never calls the backend, the runtime, or the CLI.
 */
import { computed, ref } from 'vue'
import { Copy, Check } from '@lucide/vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { HumanReviewGate } from '@/types/api/humanReviewGovernance'

const props = defineProps<{
  gate: HumanReviewGate | null
}>()

type DetailMode = 'gate' | 'empty'

const mode = computed<DetailMode>(() => (props.gate ? 'gate' : 'empty'))

/** Harmless clipboard-only copy state for the gate id: 'idle' | 'copied' | 'unavailable'. */
const copyState = ref<'idle' | 'copied' | 'unavailable'>('idle')

async function copyGateId(gateId: string): Promise<void> {
  // Clipboard is the ONLY side effect, and it is a local UI affordance — never
  // an approval, network, or file operation. Guard for environments without it.
  const clipboard = globalThis.navigator?.clipboard
  if (!clipboard || typeof clipboard.writeText !== 'function') {
    copyState.value = 'unavailable'
    return
  }
  try {
    await clipboard.writeText(gateId)
    copyState.value = 'copied'
  } catch {
    // A clipboard rejection is harmless — never fall back to an approval.
    copyState.value = 'unavailable'
  }
}
</script>

<template>
  <div
    class="devconsole-card hrgov-detail"
    data-testid="human-review-gate-detail"
    aria-label="P0 gate detail"
  >
    <div v-if="mode === 'empty'" data-testid="human-review-detail-empty">
      <EmptyState
        message="No gate selected."
        hint="Select “Inspect” on a P0 gate to view its read-only human-review detail."
      />
    </div>

    <div v-else data-testid="human-review-detail-gate">
      <div class="hrgov-detail__bar">
        <h3 class="hrgov-detail__title">
          <code>{{ gate!.gateId }}</code> — {{ gate!.title }}
        </h3>
        <button
          type="button"
          class="hrgov-copy"
          :aria-label="`Copy gate id ${gate!.gateId}`"
          data-testid="human-review-copy-gate-id"
          :data-copy-state="copyState"
          @click="copyGateId(gate!.gateId)"
        >
          <Check v-if="copyState === 'copied'" :size="13" aria-hidden="true" />
          <Copy v-else :size="13" aria-hidden="true" />
          <span>{{
            copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy ID'
          }}</span>
        </button>
      </div>

      <dl class="hrgov-dl" data-testid="human-review-detail-fields">
        <div class="hrgov-dl__row">
          <dt>Status</dt>
          <dd :data-status="gate!.status">{{ gate!.statusLabel }}</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Category</dt>
          <dd>{{ gate!.category }}</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Evidence level</dt>
          <dd>{{ gate!.evidenceLevel }}</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Resolved</dt>
          <dd :data-flag="`resolved-${gate!.resolved}`" data-testid="human-review-detail-resolved">
            {{ gate!.resolved }}
          </dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Approved</dt>
          <dd :data-flag="`approved-${gate!.approved}`" data-testid="human-review-detail-approved">
            {{ gate!.approved }}
          </dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Production authorization</dt>
          <dd :data-flag="`productionAuthorization-${gate!.productionAuthorizationImpact}`">
            {{ gate!.productionAuthorizationImpact }}
          </dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Requires human review</dt>
          <dd :data-flag="`requiresHumanReview-${gate!.requiresHumanReview}`">
            {{ gate!.requiresHumanReview }}
          </dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Required reviewer</dt>
          <dd>{{ gate!.reviewerCategory }}</dd>
        </div>
        <div class="hrgov-dl__row">
          <dt>Source phase</dt>
          <dd>{{ gate!.sourcePhase }}</dd>
        </div>
        <div class="hrgov-dl__row hrgov-dl__row--full">
          <dt>Human review requirement</dt>
          <dd>{{ gate!.humanReviewRequirement }}</dd>
        </div>
        <div class="hrgov-dl__row hrgov-dl__row--full">
          <dt>Code evidence summary</dt>
          <dd>{{ gate!.codeEvidenceSummary }}</dd>
        </div>
        <div class="hrgov-dl__row hrgov-dl__row--full">
          <dt>Blocked reason</dt>
          <dd>{{ gate!.blockedReason }}</dd>
        </div>
        <div class="hrgov-dl__row hrgov-dl__row--full">
          <dt>Related artifacts</dt>
          <dd>
            <code v-for="a in gate!.relatedArtifacts" :key="a" class="hrgov-chip">{{ a }}</code>
          </dd>
        </div>
      </dl>

      <h4 class="hrgov-detail__subhead">Forbidden actions (never offered by the WebUI)</h4>
      <ul class="hrgov-tags" data-testid="human-review-detail-forbidden-actions">
        <li v-for="action in gate!.forbiddenActions" :key="action" :data-forbidden-action="action">
          {{ action }}
        </li>
      </ul>

      <p class="hrgov-detail__note" data-testid="human-review-detail-read-only-note">
        Read-only projection — this gate is unresolved, not approved, and its
        production authorization impact is NO-GO. The WebUI cannot approve,
        authorize, sign off, resolve, or override it; resolution requires a valid
        out-of-band human review.
      </p>
    </div>
  </div>
</template>

<style scoped>
.hrgov-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.hrgov-detail__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}
.hrgov-detail__title {
  margin: 0;
  font-size: var(--font-size-md, 14px);
}
.hrgov-detail__title code {
  font-family: var(--font-mono, ui-monospace, monospace);
}
.hrgov-copy {
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
.hrgov-copy:hover {
  border-color: var(--color-accent, #6f8cff);
}
.hrgov-copy:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.hrgov-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.hrgov-dl__row {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.hrgov-dl__row--full {
  grid-column: 1 / -1;
}
.hrgov-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  word-break: break-word;
}
.hrgov-dl__row[data-status] dd,
.hrgov-dl__row .hrgov-dl__row dd {
  word-break: break-word;
}
.hrgov-chip {
  display: inline-block;
  margin: 0 var(--space-1, 4px) var(--space-1, 4px) 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-detail__subhead {
  margin: var(--space-2, 8px) 0 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.hrgov-tags li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #8a8a94);
}
.hrgov-detail__note {
  margin: var(--space-2, 8px) 0 0;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
</style>
