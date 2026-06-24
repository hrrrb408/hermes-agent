<script setup lang="ts">
/**
 * Governance Hub → Target B Readiness region (Phase 4A).
 *
 * A read-only region inside the Governance Hub that states the **Target B
 * readiness scaffold** (production plugin runtime / real plugin ecosystem) is
 * drafted while every dangerous capability stays **disabled**. Target B is the
 * long-term goal; Phase 4A implements ONLY the readiness scaffold — the
 * architecture models, the disabled interfaces, the permission / approval gate
 * models, and the read-only WebUI preview. It does NOT enable any capability.
 *
 * It projects, from frozen static data only:
 *   1. a Target B readiness banner (scaffold ready, execution disabled,
 *      production NO-GO, registry disabled, marketplace disabled, WebUI execute
 *      disabled, approval required);
 *   2. readiness summary cards;
 *   3. the architecture module board (16 designed / scaffolded-disabled modules,
 *      every one non-executing / non-networking / non-production / no route);
 *   4. a fake, static, non-executable plugin package schema preview;
 *   5. the permission model matrix (every permission denied by default);
 *   6. the registry protocol preview (a reserved .invalid URL, never fetched);
 *   7. the WebUI execution preview (a disabled flow — NO execute / run button);
 *   8. the approval / authorization gate panel (no trust token, metadata rejected);
 *   9. the enablement blockers panel;
 *  10. the Target A relationship (prerequisite evidence only);
 *  11. the readiness checklist + allowed / forbidden action panels.
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO execution, NO plugin loading, NO registry
 * fetch, NO marketplace access, NO route change, NO file or network access, and
 * NO production access. There is NO Approve / Reject / Authorize / Sign off /
 * Resolve / Override / Enable / Run / Execute / Batch / Upload / Load / Fetch /
 * Install control, NO API-key input, NO secret input, NO file picker, NO
 * signature upload, and NO JSON execution input. The WebUI execution flow is
 * rendered as disabled TEXT status items — never as an interactive execute or
 * run button. The only controls are harmless UI-only toggles: filtering the
 * architecture modules, inspecting a module, viewing the cross-linked regions,
 * and copying a read-only summary.
 *
 * Target B readiness scaffold is NOT production runtime authorized, NOT
 * arbitrary plugin loading allowed, NOT remote registry enabled, NOT marketplace
 * enabled, NOT WebUI execution enabled, NOT approval / authorization granted,
 * and NOT production rollout allowed. P0 resolved stays 0. No new backend route
 * is introduced.
 */
import { computed, ref } from 'vue'
import { Ban, Lock, ShieldCheck, ShieldX } from '@lucide/vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  buildTargetBReadinessViewModel,
  buildTargetBReadinessSummaryText,
  filterTargetBModules,
  TARGET_B_MODULE_FILTER_OPTIONS,
} from '@/lib/targetBReadinessViewModel'
import type { TargetBModuleFilterKey } from '@/types/api/targetBReadiness'

const viewModel = buildTargetBReadinessViewModel()
const nav = useDevConsoleNavStore()

/** Harmless UI-only state: the active client-side architecture module filter. */
const moduleFilter = ref<TargetBModuleFilterKey>('all')
/** Harmless UI-only state: which architecture module detail is expanded. */
const expandedModuleKey = ref<string | null>(null)

const filteredModules = computed(() => filterTargetBModules(moduleFilter.value))

function setFilter(key: TargetBModuleFilterKey): void {
  // Client-only filter on static data — no backend call, no SPA route change.
  moduleFilter.value = key
}

function toggleInspect(key: string): void {
  // Client-only detail toggle — no backend call.
  expandedModuleKey.value = expandedModuleKey.value === key ? null : key
}

/** Linked sections the region may cross-link to (a client-only section switch). */
type LinkedSection = 'runtimeGovernance' | 'humanReview'

function onNavigate(target: string | undefined): void {
  if (target === 'runtimeGovernance' || target === 'humanReview') {
    // Client-only section switch — no backend call, no SPA route change.
    nav.setSection(target as LinkedSection)
  }
}

/** Harmless UI-only state: copy feedback (copied / unavailable / idle). */
const copyState = ref<'idle' | 'copied' | 'unavailable'>('idle')

async function onCopySummary(): Promise<void> {
  const text = buildTargetBReadinessSummaryText()
  try {
    const clipboard = (globalThis.navigator as { clipboard?: { writeText?(t: string): Promise<void> } } | undefined)?.clipboard
    if (!clipboard || typeof clipboard.writeText !== 'function') {
      copyState.value = 'unavailable'
      return
    }
    await clipboard.writeText(text)
    copyState.value = 'copied'
  } catch {
    copyState.value = 'unavailable'
  }
}
</script>

<template>
  <section
    class="devconsole-card target-b-region"
    aria-label="Target B Readiness Scaffold"
    data-testid="governance-hub-target-b-region"
  >
    <header class="target-b-region__header">
      <h2 data-testid="governance-hub-target-b-heading">
        Target B — Production Runtime / Real Plugin Ecosystem Readiness Scaffold
      </h2>
      <p class="ghub-muted">
        Target B is the long-term goal of opening a real production plugin runtime
        (signed / arbitrary plugin loading, a remote registry, a marketplace, WebUI
        execution, and a production rollout). Phase 4A implements <strong>only the
        readiness scaffold</strong> — the architecture models, the disabled
        interfaces, the permission / approval gate models, and this read-only WebUI
        preview. <strong>It does not enable any capability.</strong> Execution stays
        DISABLED, every authorization stays NO-GO, and P0 resolved stays 0.
      </p>
      <ul
        class="ghub-status-badges"
        data-testid="governance-hub-target-b-status-badges"
        aria-label="Target B readiness status"
      >
        <li
          v-for="badge in viewModel.statusBadges"
          :key="badge.label"
          class="ghub-status-badge"
          :data-status-badge="badge.label"
        >
          {{ badge.label }}
        </li>
      </ul>
    </header>

    <!-- 1. Target B readiness banner -->
    <div
      class="target-b-banner"
      data-testid="governance-hub-target-b-banner"
      role="group"
      aria-label="Target B readiness status"
    >
      <div class="target-b-banner__verdict" data-target-b-verdict="SCAFFOLD_READY">
        <ShieldCheck :size="16" aria-hidden="true" />
        <span>Target B: READINESS SCAFFOLD</span>
      </div>
      <ul class="target-b-banner__lines" data-testid="governance-hub-target-b-banner-lines">
        <li data-banner-line="readiness-scaffold">Target B readiness scaffold</li>
        <li data-banner-line="execution-disabled">Execution disabled</li>
        <li data-banner-line="production-nogo">Production runtime NO-GO</li>
        <li data-banner-line="registry-disabled">Registry disabled</li>
        <li data-banner-line="marketplace-disabled">Marketplace disabled</li>
        <li data-banner-line="webui-execute-disabled">WebUI execute disabled</li>
        <li data-banner-line="approval-required">Approval required</li>
      </ul>
      <div class="target-b-banner__copy">
        <button
          type="button"
          class="ghub-copy-btn"
          :data-copy-state="copyState"
          data-testid="governance-hub-target-b-copy-summary"
          @click="onCopySummary"
        >
          {{ copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy Target B readiness summary' }}
        </button>
      </div>
    </div>

    <!-- 2. Readiness summary cards -->
    <h3>Target B readiness summary</h3>
    <StatusSummaryCards :cards="viewModel.summaryCards" />

    <!-- 3. Architecture module board -->
    <div class="target-b-block" data-testid="governance-hub-target-b-architecture">
      <h3>Architecture modules</h3>
      <p class="ghub-muted">
        Sixteen designed / scaffolded-disabled modules. Every one is disabled,
        non-executing, non-networking, non-production, and adds no route. The
        status filter is a harmless client-only toggle on static data.
      </p>
      <div class="target-b-filter" role="group" aria-label="Filter architecture modules">
        <button
          v-for="opt in TARGET_B_MODULE_FILTER_OPTIONS"
          :key="opt.key"
          type="button"
          class="target-b-filter-btn"
          :data-testid="`governance-hub-target-b-module-filter-${opt.key}`"
          :data-filter-active="moduleFilter === opt.key"
          :aria-pressed="moduleFilter === opt.key"
          @click="setFilter(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>
      <div class="ghub-board-scroll" role="region" aria-label="Target B architecture modules" tabindex="0">
        <table class="ghub-board" data-testid="governance-hub-target-b-architecture-table">
          <caption class="ghub-board__caption">
            Target B architecture modules (read-only). Columns: module, status,
            enabled, execution-capable, network-capable, production-capable, route
            impact, risk level, required gate.
          </caption>
          <thead>
            <tr>
              <th scope="col">Module</th>
              <th scope="col">Status</th>
              <th scope="col">Enabled</th>
              <th scope="col">Execution</th>
              <th scope="col">Network</th>
              <th scope="col">Production</th>
              <th scope="col">Route</th>
              <th scope="col">Risk</th>
              <th scope="col"><span class="ghub-sr-only">Inspect</span></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="m in filteredModules" :key="m.key">
              <tr :data-module-key="m.key" :data-module-status="m.status">
                <td><span class="ghub-board__name">{{ m.module }}</span></td>
                <td><span class="ghub-board__status ghub-board__status--muted" :data-status="m.status">{{ m.status }}</span></td>
                <td><span data-enabled="false" class="ghub-board__verdict"><ShieldX :size="12" aria-hidden="true" /> false</span></td>
                <td><span :data-execution-capable="m.executionCapable">{{ m.executionCapable }}</span></td>
                <td><span :data-network-capable="m.networkCapable">{{ m.networkCapable }}</span></td>
                <td><span :data-production-capable="m.productionCapable">{{ m.productionCapable }}</span></td>
                <td>{{ m.routeImpact }}</td>
                <td><span :data-risk="m.riskLevel">{{ m.riskLevel }}</span></td>
                <td>
                  <button
                    type="button"
                    class="ghub-board__link"
                    :data-testid="`governance-hub-target-b-module-inspect-${m.key}`"
                    :aria-expanded="expandedModuleKey === m.key"
                    aria-label="Inspect module details"
                    @click="toggleInspect(m.key)"
                  >
                    Inspect
                  </button>
                </td>
              </tr>
              <tr v-if="expandedModuleKey === m.key" :data-module-detail="m.key">
                <td colspan="9" class="ghub-board__detail">
                  <p><strong>Required gate:</strong> {{ m.requiredGate }}</p>
                  <p><strong>Future implementation notes:</strong> {{ m.futureImplementationNotes }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 4. Plugin package schema preview -->
    <div class="target-b-block" data-testid="governance-hub-target-b-plugin-package">
      <h3>Plugin package schema preview</h3>
      <p class="ghub-muted">
        A fake, static, non-executable schema preview. No real plugin file is loaded,
        no entrypoint is executed, no registry source is fetched, and no checksum is
        verified.
      </p>
      <ul class="target-b-tags target-b-tags--ban" data-testid="governance-hub-target-b-plugin-package-markers">
        <li><Ban :size="12" aria-hidden="true" /> Example only</li>
        <li><Ban :size="12" aria-hidden="true" /> Not loaded</li>
        <li><Ban :size="12" aria-hidden="true" /> Not executable</li>
        <li><Ban :size="12" aria-hidden="true" /> No file read</li>
        <li><Ban :size="12" aria-hidden="true" /> No install</li>
      </ul>
      <dl class="ghub-dl" data-testid="governance-hub-target-b-plugin-package-fields">
        <div class="ghub-dl__row"><dt>Package id</dt><dd>{{ viewModel.pluginPackageSchema.packageId }}</dd></div>
        <div class="ghub-dl__row"><dt>Version</dt><dd>{{ viewModel.pluginPackageSchema.version }}</dd></div>
        <div class="ghub-dl__row"><dt>Descriptor</dt><dd>{{ viewModel.pluginPackageSchema.descriptor }}</dd></div>
        <div class="ghub-dl__row"><dt>Capabilities</dt><dd>{{ viewModel.pluginPackageSchema.capabilities.join(', ') }}</dd></div>
        <div class="ghub-dl__row"><dt>Permissions</dt><dd>{{ viewModel.pluginPackageSchema.permissions.join(', ') }}</dd></div>
        <div class="ghub-dl__row"><dt>Entrypoints</dt><dd>{{ viewModel.pluginPackageSchema.entrypoints.join(', ') }}</dd></div>
        <div class="ghub-dl__row"><dt>Signature</dt><dd>{{ viewModel.pluginPackageSchema.signature }}</dd></div>
        <div class="ghub-dl__row"><dt>Publisher</dt><dd>{{ viewModel.pluginPackageSchema.publisher }}</dd></div>
        <div class="ghub-dl__row"><dt>Registry source</dt><dd>{{ viewModel.pluginPackageSchema.registrySource }}</dd></div>
        <div class="ghub-dl__row"><dt>Checksum</dt><dd>{{ viewModel.pluginPackageSchema.checksum }}</dd></div>
        <div class="ghub-dl__row"><dt>Sandbox profile</dt><dd>{{ viewModel.pluginPackageSchema.sandboxProfile }}</dd></div>
        <div class="ghub-dl__row"><dt>Minimum Hermes version</dt><dd>{{ viewModel.pluginPackageSchema.minimumHermesVersion }}</dd></div>
      </dl>
    </div>

    <!-- 5. Permission model matrix -->
    <div class="target-b-block" data-testid="governance-hub-target-b-permission">
      <h3>Permission model</h3>
      <p class="ghub-muted">
        Every permission is <strong>denied by default</strong>. None is granted, no
        matter what renders or what untrusted metadata a request carries.
      </p>
      <div class="ghub-board-scroll" role="region" aria-label="Target B permission model" tabindex="0">
        <table class="ghub-board" data-testid="governance-hub-target-b-permission-table">
          <caption class="ghub-board__caption">
            Target B permissions (read-only). Every status is DENIED_BY_DEFAULT.
          </caption>
          <thead>
            <tr>
              <th scope="col">Permission</th>
              <th scope="col">Label</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="p in viewModel.permissionModel.entries"
              :key="p.key"
              :data-permission-key="p.key"
            >
              <td><code>{{ p.key }}</code></td>
              <td>{{ p.label }}</td>
              <td><span class="ghub-board__verdict" :data-permission-status="p.currentStatus"><ShieldX :size="12" aria-hidden="true" /> {{ p.currentStatus }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 6. Registry protocol preview -->
    <div class="target-b-block" data-testid="governance-hub-target-b-registry">
      <h3>Registry protocol preview</h3>
      <p class="ghub-muted">
        The registry URL is a documentation string using a reserved
        <code>.invalid</code> domain — it is never fetched.
      </p>
      <dl class="ghub-dl">
        <div class="ghub-dl__row"><dt>Registry URL (example)</dt><dd data-registry-url>{{ viewModel.registryProtocol.registryUrlExample }}</dd></div>
        <div class="ghub-dl__row"><dt>Fetch enabled</dt><dd :data-registry-fetch="viewModel.registryProtocol.fetchEnabled">{{ viewModel.registryProtocol.fetchEnabled }}</dd></div>
        <div class="ghub-dl__row"><dt>Network enabled</dt><dd :data-registry-network="viewModel.registryProtocol.networkEnabled">{{ viewModel.registryProtocol.networkEnabled }}</dd></div>
        <div class="ghub-dl__row"><dt>Trust policy required</dt><dd>{{ viewModel.registryProtocol.trustPolicyRequired }}</dd></div>
        <div class="ghub-dl__row"><dt>Signature required</dt><dd :data-signature-required="viewModel.registryProtocol.signatureRequired">{{ viewModel.registryProtocol.signatureRequired }}</dd></div>
        <div class="ghub-dl__row"><dt>Allow unsigned</dt><dd :data-allow-unsigned="viewModel.registryProtocol.allowUnsigned">{{ viewModel.registryProtocol.allowUnsigned }}</dd></div>
        <div class="ghub-dl__row"><dt>Marketplace enabled</dt><dd :data-marketplace-enabled="viewModel.registryProtocol.marketplaceEnabled">{{ viewModel.registryProtocol.marketplaceEnabled }}</dd></div>
      </dl>
    </div>

    <!-- 7. WebUI execution preview (disabled flow — NO execute / run button) -->
    <div class="target-b-block" data-testid="governance-hub-target-b-execution">
      <h3>WebUI execution preview</h3>
      <p class="ghub-muted">
        The execution flow is visible but every step is <strong>disabled</strong>.
        There is no execute button, no run button, no form, no input, and no submit
        control. The flow is rendered as disabled TEXT status items only.
      </p>
      <ul class="target-b-flow" data-testid="governance-hub-target-b-execution-flow">
        <li
          v-for="step in viewModel.webuiExecution.flow"
          :key="step.key"
          :data-flow-step="step.key"
          :data-flow-enabled="step.enabled"
        >
          <span class="target-b-flow__label">{{ step.label }}</span>
          <span class="target-b-flow__note" :data-flow-note="step.note">{{ step.note }}</span>
        </li>
      </ul>
      <p class="ghub-muted">
        Execute button enabled: <strong :data-execute-button-enabled="viewModel.webuiExecution.executeButtonEnabled">{{ viewModel.webuiExecution.executeButtonEnabled }}</strong>
        · Runtime route available: <strong :data-runtime-route-available="viewModel.webuiExecution.runtimeRouteAvailable">{{ viewModel.webuiExecution.runtimeRouteAvailable }}</strong>
        · Can submit: <strong :data-can-submit="viewModel.webuiExecution.canSubmit">{{ viewModel.webuiExecution.canSubmit }}</strong>
        · Status: <strong :data-execution-status="viewModel.webuiExecution.status">{{ viewModel.webuiExecution.status }}</strong>
      </p>
    </div>

    <!-- 8. Approval / authorization gate panel -->
    <div class="target-b-block" data-testid="governance-hub-target-b-approval">
      <h3>Approval / authorization gate</h3>
      <dl class="ghub-dl">
        <div class="ghub-dl__row"><dt>Human approval required</dt><dd :data-human-approval-required="viewModel.approvalGate.humanApprovalRequired">{{ viewModel.approvalGate.humanApprovalRequired }}</dd></div>
        <div class="ghub-dl__row"><dt>Trust token provisioned</dt><dd :data-trust-token-provisioned="viewModel.approvalGate.trustTokenProvisioned">{{ viewModel.approvalGate.trustTokenProvisioned }}</dd></div>
        <div class="ghub-dl__row"><dt>Fake approval accepted</dt><dd :data-fake-approval-accepted="viewModel.approvalGate.fakeApprovalAccepted">{{ viewModel.approvalGate.fakeApprovalAccepted }}</dd></div>
        <div class="ghub-dl__row"><dt>AI approval accepted</dt><dd :data-ai-approval-accepted="viewModel.approvalGate.aiApprovalAccepted">{{ viewModel.approvalGate.aiApprovalAccepted }}</dd></div>
        <div class="ghub-dl__row"><dt>Metadata approval accepted</dt><dd :data-metadata-approval-accepted="viewModel.approvalGate.metadataApprovalAccepted">{{ viewModel.approvalGate.metadataApprovalAccepted }}</dd></div>
        <div class="ghub-dl__row"><dt>Production authorization</dt><dd :data-production-authorization="viewModel.approvalGate.productionAuthorization">{{ viewModel.approvalGate.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 9. Enablement blockers -->
    <div class="target-b-block" data-testid="governance-hub-target-b-enablement-blockers">
      <h3>Enablement blockers</h3>
      <p class="ghub-muted">
        What must be completed before Target B could even be considered. Every
        blocker stays unresolved.
      </p>
      <ul class="target-b-blockers">
        <li
          v-for="b in viewModel.enablementBlockers"
          :key="b.key"
          :data-blocker-key="b.key"
          :data-blocker-resolved="b.resolved"
        >
          <Lock :size="13" aria-hidden="true" />
          <div>
            <span class="target-b-blockers__label">{{ b.label }}</span>
            <span class="target-b-blockers__detail">{{ b.detail }}</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- 10. Target A relationship -->
    <div class="target-b-block" data-testid="governance-hub-target-b-target-a-relationship">
      <h3>Relationship to Target A</h3>
      <ul class="target-a-rel">
        <li
          v-for="r in viewModel.targetARelationship"
          :key="r.key"
          :data-relationship-key="r.key"
        >
          <ShieldCheck :size="13" aria-hidden="true" />
          <span>{{ r.statement }}</span>
        </li>
      </ul>
      <div class="target-a-rel__links">
        <button
          type="button"
          class="ghub-board__link"
          data-testid="governance-hub-target-b-view-target-a"
          aria-label="View Target A region"
          @click="onNavigate('runtimeGovernance')"
        >
          View Target A region
        </button>
        <button
          type="button"
          class="ghub-board__link"
          data-testid="governance-hub-target-b-view-runtime-governance"
          aria-label="View Runtime Governance section"
          @click="onNavigate('runtimeGovernance')"
        >
          View Runtime Governance
        </button>
        <button
          type="button"
          class="ghub-board__link"
          data-testid="governance-hub-target-b-view-human-review"
          aria-label="View Human Review section"
          @click="onNavigate('humanReview')"
        >
          View Human Review
        </button>
      </div>
    </div>

    <!-- 11. Readiness checklist -->
    <div class="target-b-block" data-testid="governance-hub-target-b-readiness">
      <h3>Readiness checklist</h3>
      <p class="ghub-muted">
        Design-drafting items are <strong>ready</strong>; production-enablement
        items are <strong>blocked</strong>. None says the system is production-ready.
      </p>
      <ul class="target-b-checklist" data-testid="governance-hub-target-b-readiness-list">
        <li
          v-for="item in viewModel.readinessChecklist"
          :key="item.id"
          :data-readiness-id="item.id"
          :data-readiness-status="item.status"
          :data-enablement-blocked="item.enablementBlocked"
        >
          <ShieldCheck v-if="item.status === 'ready'" :size="13" aria-hidden="true" />
          <ShieldX v-else :size="13" aria-hidden="true" />
          <div class="target-b-checklist__body">
            <span class="target-b-checklist__label">
              {{ item.label }}
              <strong class="target-b-checklist__status" :data-status="item.status">{{ item.status }}</strong>
            </span>
            <span class="target-b-checklist__evidence">{{ item.evidenceSummary }}</span>
          </div>
        </li>
      </ul>
    </div>

    <!-- Allowed / forbidden action panels -->
    <div class="target-b-block" data-testid="governance-hub-target-b-actions">
      <h3>What this region can and cannot do</h3>
      <div class="ghub-actions">
        <div class="ghub-actions__group">
          <h4>Allowed (read-only)</h4>
          <ul class="ghub-tags ghub-tags--ok" data-testid="governance-hub-target-b-allowed-actions">
            <li v-for="action in viewModel.allowedUiActions" :key="action" :data-allowed-action="action">{{ action }}</li>
          </ul>
        </div>
        <div class="ghub-actions__group">
          <h4>Forbidden (never offered)</h4>
          <ul class="ghub-tags ghub-tags--ban" data-testid="governance-hub-target-b-forbidden-actions">
            <li v-for="action in viewModel.forbiddenActions" :key="action" :data-forbidden-action="action">{{ action }}</li>
          </ul>
        </div>
      </div>
    </div>

    <p class="ghub-muted target-b-region__footer">
      This region is a read-only readiness scaffold. It is not an authorization, not
      an approval, not a signoff, not a closeout, and not production authorization.
      Production plugin runtime, arbitrary plugin loading, remote registry,
      marketplace, external network, real API keys, WebUI execution, approval /
      authorization, and production rollout all remain NO-GO / disabled.
    </p>
  </section>
</template>

<style scoped>
.target-b-region {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.target-b-region__header h2 {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-region__header p {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-region__footer {
  margin-top: var(--space-1, 4px);
}
.ghub-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.ghub-sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
.ghub-status-badges {
  list-style: none;
  margin: var(--space-2, 8px) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-status-badge {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  background: var(--color-surface, #101015);
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-xs, 12px);
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  white-space: nowrap;
}
.ghub-copy-btn,
.target-b-filter-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.target-b-filter-btn {
  font-weight: 600;
}
.target-b-filter-btn[data-filter-active='true'] {
  border-color: var(--color-accent, #6f8cff);
  color: var(--color-accent, #6f8cff);
}
.ghub-copy-btn:hover,
.target-b-filter-btn:hover,
.ghub-board__link:hover {
  border-color: var(--color-accent, #6f8cff);
}
.ghub-copy-btn:focus-visible,
.target-b-filter-btn:focus-visible,
.ghub-board__link:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.target-b-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.target-b-banner__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  color: var(--color-success, #6ec48e);
  font-weight: 700;
  font-size: var(--font-size-base, 15px);
}
.target-b-banner__lines {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-b-banner__lines li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text, #e6e6ec);
}
.target-b-block h3 {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-block p.ghub-muted {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.ghub-board-scroll {
  overflow-x: auto;
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
}
.ghub-board {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  min-width: 820px;
}
.ghub-board__caption {
  text-align: left;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-board th,
.ghub-board td {
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-bottom: 1px solid var(--color-border, #2a2a33);
  vertical-align: top;
}
.ghub-board thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
  font-size: var(--font-size-xs, 12px);
}
.ghub-board__name {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.ghub-board__status {
  font-weight: 600;
}
.ghub-board__status--muted {
  color: var(--color-text-muted, #8a8a94);
}
.ghub-board__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  color: var(--color-danger, #e0566a);
  font-weight: 600;
}
.ghub-board__detail {
  background: var(--color-surface, #101015);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.6;
}
.ghub-board__detail p {
  margin: var(--space-1, 4px) 0;
}
.ghub-board__link {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: 1px var(--space-1, 4px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.target-b-tags {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.target-b-tags li {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #8a8a94);
}
.ghub-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.ghub-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.ghub-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.ghub-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  text-align: right;
  word-break: break-word;
}
.target-b-flow {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-b-flow li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  background: var(--color-surface, #101015);
}
.target-b-flow__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  font-weight: 600;
}
.target-b-flow__note {
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text-muted, #8a8a94);
}
.target-b-blockers {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-b-blockers li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
  color: var(--color-danger, #e0566a);
}
.target-b-blockers__label {
  display: block;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  font-weight: 600;
}
.target-b-blockers__detail {
  display: block;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.target-a-rel {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.target-a-rel li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
  color: var(--color-text, #e6e6ec);
  font-size: var(--font-size-sm, 13px);
}
.target-a-rel__links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.target-b-checklist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.target-b-checklist li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
}
.target-b-checklist li[data-readiness-status='ready'] {
  color: var(--color-success, #6ec48e);
}
.target-b-checklist li[data-readiness-status='blocked'] {
  color: var(--color-danger, #e0566a);
}
.target-b-checklist__body {
  display: flex;
  flex-direction: column;
  gap: var(--space-1, 4px);
}
.target-b-checklist__label {
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
}
.target-b-checklist__status {
  margin-left: var(--space-2, 8px);
  text-transform: uppercase;
}
.target-b-checklist li[data-readiness-status='ready'] .target-b-checklist__status {
  color: var(--color-success, #6ec48e);
}
.target-b-checklist li[data-readiness-status='blocked'] .target-b-checklist__status {
  color: var(--color-danger, #e0566a);
}
.target-b-checklist__evidence {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.ghub-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.ghub-actions__group h4 {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.ghub-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.ghub-tags li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.ghub-tags--ok li {
  color: var(--color-success, #6ec48e);
}
.ghub-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
</style>
