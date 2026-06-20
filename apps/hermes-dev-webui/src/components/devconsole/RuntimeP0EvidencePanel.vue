<script setup lang="ts">
/**
 * Runtime Governance P0 evidence panel (Phase 3J).
 *
 * Read-only projection of the conservative P0 evidence summary for the dev-only
 * descriptor-backed fixture runtime. resolvedCount is always 0 and every
 * authorization flag is frozen NO-GO / not-authorized. A descriptor-backed
 * fixture pass is dev-only partial evidence — it never resolves a gate and
 * never authorizes production or a real runtime.
 */
import type { RuntimeP0EvidenceProjection } from '@/types/api/runtimeGovernance'

defineProps<{
  evidence: RuntimeP0EvidenceProjection
}>()
</script>

<template>
  <div class="devconsole-card" data-testid="runtime-p0-evidence-panel">
    <h3>P0 evidence projection</h3>
    <p class="rtgov-muted">{{ evidence.classificationNote }}</p>

    <dl class="rtgov-dl" data-testid="runtime-p0-counts">
      <div class="rtgov-dl__row">
        <dt>Total P0 gates</dt>
        <dd data-testid="runtime-p0-total">{{ evidence.totalGates }}</dd>
      </div>
      <div class="rtgov-dl__row rtgov-dl__row--warn">
        <dt>Resolved / approved</dt>
        <dd data-testid="runtime-p0-resolved">{{ evidence.resolvedCount }}</dd>
      </div>
      <div class="rtgov-dl__row">
        <dt>Partial evidence</dt>
        <dd>{{ evidence.partialEvidenceCount }}</dd>
      </div>
      <div class="rtgov-dl__row">
        <dt>Candidate for review</dt>
        <dd>{{ evidence.candidateForReviewCount }}</dd>
      </div>
      <div class="rtgov-dl__row">
        <dt>Pending human review</dt>
        <dd>{{ evidence.blockedByHumanReviewCount }}</dd>
      </div>
      <div class="rtgov-dl__row">
        <dt>Governance-only / no evidence</dt>
        <dd>{{ evidence.governanceOnlyCount + evidence.noEvidenceCount }}</dd>
      </div>
      <div class="rtgov-dl__row">
        <dt>Unresolved</dt>
        <dd>{{ evidence.unresolvedCount }}</dd>
      </div>
    </dl>

    <ul class="rtgov-authz" data-testid="runtime-p0-authorization">
      <li>
        <span>Implementation Authorization</span>
        <strong data-testid="runtime-p0-implementation-gate">{{ evidence.implementationAuthorization }}</strong>
      </li>
      <li>
        <span>Phase 3I production authorization</span>
        <strong data-testid="runtime-p0-phase3i-gate">{{
          evidence.phase3iAuthorized ? 'AUTHORIZED' : 'NOT_AUTHORIZED'
        }}</strong>
      </li>
      <li>
        <span>Production runtime</span>
        <strong>{{ evidence.realRuntime }}</strong>
      </li>
      <li>
        <span>New route</span>
        <strong>{{ evidence.newRoute }}</strong>
      </li>
      <li>
        <span>Production rollout</span>
        <strong>{{ evidence.productionRollout }}</strong>
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
.rtgov-dl {
  margin: 0 0 var(--space-3, 12px);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.rtgov-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.rtgov-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.rtgov-dl__row--warn dd {
  color: var(--color-warning, #d9a441);
}
.rtgov-authz {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.rtgov-authz li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-authz li span {
  color: var(--color-text-muted, #8a8a94);
}
.rtgov-authz li strong {
  color: var(--color-danger, #e0566a);
}
</style>
