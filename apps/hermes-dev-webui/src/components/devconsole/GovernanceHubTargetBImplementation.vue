<script setup lang="ts">
/**
 * Governance Hub → Target B End-to-End Implementation region (Phase 4B).
 *
 * A read-only region inside the Governance Hub that states the **Target B
 * end-to-end implementation** (production plugin runtime / real plugin
 * ecosystem) is drafted — the full engineering path: the signed package schema,
 * the signature verifier interface, the permission / capability model, the
 * registry trust policy, the sandbox broker, the execution policy gate, the
 * approval / authorization gate, the runtime orchestrator, the audit trail,
 * and the rollback / kill switch — while every dangerous capability stays
 * **disabled / gated**. It does NOT enable any capability.
 *
 * It projects, from frozen static data only:
 *   1. a Target B implementation banner (scaffold ready, execution disabled,
 *      production NO-GO, WebUI execute disabled, registry disabled, marketplace
 *      disabled, approval NO-GO, P0 resolved 0);
 *   2. implementation summary cards;
 *   3. the implementation layer board (12 drafted layers, every one disabled /
 *      non-executing / non-networking / non-production / no route);
 *   4. a fake, static, non-executable signed plugin package schema preview;
 *   5. the signature verification panel (interface implemented, production
 *      verifier NOT authorized, fixture-only, unsigned / forged rejected);
 *   6. the permission model matrix (15 permissions, every one denied by
 *      default) + the non-executable capability model;
 *   7. the registry trust panel (mode DISABLED, network off, marketplace off);
 *   8. the sandbox broker panel (interface implemented, broker disabled, no
 *      process spawn / network / filesystem write / secrets);
 *   9. the approval / authorization gate panel (human approval required, no
 *      trust token, fake / AI / metadata approval rejected);
 *  10. the execution policy panel (allowed false, webui execute disabled,
 *      runtime route disabled, production runtime disabled);
 *  11. the audit / rollback panel (in-memory only, kill switch design-ready
 *      only, production rollout NO-GO);
 *  12. the enablement blockers panel;
 *  13. the allowed / forbidden action panels.
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO execution, NO plugin loading, NO registry
 * fetch, NO marketplace access, NO route change, NO file or network access, and
 * NO production access. There is NO Approve / Reject / Authorize / Sign off /
 * Resolve / Override / Enable / Run / Execute / Batch / Upload / Load / Fetch /
 * Install control, NO API-key input, NO secret input, NO file picker, NO
 * signature upload, and NO JSON execution input. The execution policy flow is
 * rendered as disabled TEXT status items — never as an interactive execute or
 * run button. The only controls are harmless UI-only toggles: filtering the
 * implementation layers, inspecting a layer, viewing the cross-linked regions,
 * and copying a read-only summary.
 *
 * Target B implementation is NOT production runtime authorized, NOT arbitrary
 * plugin loading allowed, NOT remote registry enabled, NOT marketplace enabled,
 * NOT WebUI execution enabled, NOT approval / authorization granted, and NOT
 * production rollout allowed. P0 resolved stays 0. No new backend route is
 * introduced.
 */
import { computed, ref } from 'vue'
import { Ban, Lock, ShieldCheck, ShieldX } from '@lucide/vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  buildTargetBImplementationViewModel,
  buildTargetBImplementationSummaryText,
  filterTargetBImplementationLayers,
  TARGET_B_LAYER_FILTER_OPTIONS,
} from '@/lib/targetBImplementationViewModel'
import type { TargetBLayerFilterKey } from '@/types/api/targetBImplementation'

const viewModel = buildTargetBImplementationViewModel()
const nav = useDevConsoleNavStore()

/** Harmless UI-only state: the active client-side implementation layer filter. */
const layerFilter = ref<TargetBLayerFilterKey>('all')
/** Harmless UI-only state: which implementation layer detail is expanded. */
const expandedLayerKey = ref<string | null>(null)

const filteredLayers = computed(() => filterTargetBImplementationLayers(layerFilter.value))

function setFilter(key: TargetBLayerFilterKey): void {
  // Client-only filter on static data — no backend call, no SPA route change.
  layerFilter.value = key
}

function toggleInspect(key: string): void {
  // Client-only detail toggle — no backend call.
  expandedLayerKey.value = expandedLayerKey.value === key ? null : key
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
  const text = buildTargetBImplementationSummaryText()
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
    class="devconsole-card target-b-impl"
    aria-label="Target B End-to-End Implementation (gated)"
    data-testid="governance-hub-target-b-impl-region"
  >
    <header class="target-b-impl__header">
      <h2 data-testid="governance-hub-target-b-impl-heading">
        Target B — End-to-End Implementation (Gated)
      </h2>
      <p class="tbi-muted">
        Phase 4B drafts the <strong>full engineering path</strong> for the Target B
        production plugin runtime — the signed package schema, the signature
        verifier interface, the permission / capability model, the registry trust
        policy, the sandbox broker, the execution policy gate, the approval /
        authorization gate, the runtime orchestrator, the audit trail, and the
        rollback / kill switch. <strong>Every capability stays gated and
        disabled.</strong> Execution stays DISABLED, every authorization stays
        NO-GO, and P0 resolved stays 0.
      </p>
      <ul
        class="tbi-status-badges"
        data-testid="governance-hub-target-b-impl-status-badges"
        aria-label="Target B implementation status"
      >
        <li
          v-for="badge in viewModel.statusBadges"
          :key="badge.label"
          class="tbi-status-badge"
          :data-status-badge="badge.label"
        >
          {{ badge.label }}
        </li>
      </ul>
    </header>

    <!-- 1. Target B implementation banner -->
    <div
      class="tbi-banner"
      data-testid="governance-hub-target-b-impl-banner"
      role="group"
      aria-label="Target B implementation status"
    >
      <div class="tbi-banner__verdict" data-impl-verdict="SCAFFOLD_READY">
        <ShieldCheck :size="16" aria-hidden="true" />
        <span>Target B: IMPLEMENTATION SCAFFOLD (gated)</span>
      </div>
      <ul class="tbi-banner__lines" data-testid="governance-hub-target-b-impl-banner-lines">
        <li data-banner-line="implementation-scaffold">Implementation scaffold</li>
        <li data-banner-line="execution-disabled">Execution disabled</li>
        <li data-banner-line="production-nogo">Production runtime NO-GO</li>
        <li data-banner-line="webui-execute-disabled">WebUI execute disabled</li>
        <li data-banner-line="registry-disabled">Registry disabled</li>
        <li data-banner-line="marketplace-disabled">Marketplace disabled</li>
        <li data-banner-line="approval-nogo">Approval NO-GO</li>
        <li data-banner-line="p0-zero">P0 resolved 0</li>
      </ul>
      <div class="tbi-banner__copy">
        <button
          type="button"
          class="tbi-copy-btn"
          :data-copy-state="copyState"
          data-testid="governance-hub-target-b-impl-copy-summary"
          @click="onCopySummary"
        >
          {{ copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy Target B implementation summary' }}
        </button>
      </div>
    </div>

    <!-- 2. Implementation summary cards -->
    <h3>Target B implementation summary</h3>
    <StatusSummaryCards :cards="viewModel.summaryCards" />

    <!-- 3. Implementation layer board -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-layers">
      <h3>Implementation layers</h3>
      <p class="tbi-muted">
        Twelve drafted layers. Every one is disabled, non-executing,
        non-networking, non-production, and adds no route. The status filter is
        a harmless client-only toggle on static data.
      </p>
      <div class="tbi-filter" role="group" aria-label="Filter implementation layers">
        <button
          v-for="opt in TARGET_B_LAYER_FILTER_OPTIONS"
          :key="opt.key"
          type="button"
          class="tbi-filter-btn"
          :data-testid="`governance-hub-target-b-impl-layer-filter-${opt.key}`"
          :data-filter-active="layerFilter === opt.key"
          :aria-pressed="layerFilter === opt.key"
          @click="setFilter(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>
      <div class="tbi-board-scroll" role="region" aria-label="Target B implementation layers" tabindex="0">
        <table class="tbi-board" data-testid="governance-hub-target-b-impl-layers-table">
          <caption class="tbi-board__caption">
            Target B implementation layers (read-only). Columns: layer, status,
            enabled, execution-capable, network-capable, production-capable, risk,
            required gate.
          </caption>
          <thead>
            <tr>
              <th scope="col">Layer</th>
              <th scope="col">Status</th>
              <th scope="col">Enabled</th>
              <th scope="col">Execution</th>
              <th scope="col">Network</th>
              <th scope="col">Production</th>
              <th scope="col">Risk</th>
              <th scope="col"><span class="tbi-sr-only">Inspect</span></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="l in filteredLayers" :key="l.key">
              <tr :data-layer-key="l.key" :data-layer-status="l.status">
                <td><span class="tbi-board__name">{{ l.layer }}</span></td>
                <td><span class="tbi-board__status tbi-board__status--muted" :data-status="l.status">{{ l.status }}</span></td>
                <td><span data-enabled="false" class="tbi-board__verdict"><ShieldX :size="12" aria-hidden="true" /> false</span></td>
                <td><span :data-execution-capable="l.executionCapable">{{ l.executionCapable }}</span></td>
                <td><span :data-network-capable="l.networkCapable">{{ l.networkCapable }}</span></td>
                <td><span :data-production-capable="l.productionCapable">{{ l.productionCapable }}</span></td>
                <td><span :data-risk="l.riskLevel">{{ l.riskLevel }}</span></td>
                <td>
                  <button
                    type="button"
                    class="tbi-board__link"
                    :data-testid="`governance-hub-target-b-impl-layer-inspect-${l.key}`"
                    :aria-expanded="expandedLayerKey === l.key"
                    aria-label="Inspect layer details"
                    @click="toggleInspect(l.key)"
                  >
                    Inspect
                  </button>
                </td>
              </tr>
              <tr v-if="expandedLayerKey === l.key" :data-layer-detail="l.key">
                <td colspan="8" class="tbi-board__detail">
                  <p><strong>Required gate:</strong> {{ l.requiredGate }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 4. Signed plugin package schema preview -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-package">
      <h3>Signed plugin package schema preview</h3>
      <p class="tbi-muted">
        A fake, static, non-executable signed package schema preview. No real
        plugin file is loaded, no entrypoint is executed, no registry source is
        fetched, no checksum is computed, and no signature is verified.
      </p>
      <ul class="tbi-tags tbi-tags--ban" data-testid="governance-hub-target-b-impl-package-markers">
        <li><Ban :size="12" aria-hidden="true" /> Example only</li>
        <li><Ban :size="12" aria-hidden="true" /> Not loaded</li>
        <li><Ban :size="12" aria-hidden="true" /> Not executable</li>
        <li><Ban :size="12" aria-hidden="true" /> No file read</li>
        <li><Ban :size="12" aria-hidden="true" /> No install</li>
      </ul>
      <dl class="tbi-dl" data-testid="governance-hub-target-b-impl-package-fields">
        <div class="tbi-dl__row"><dt>Package id</dt><dd>{{ viewModel.packageSchema.packageId }}</dd></div>
        <div class="tbi-dl__row"><dt>Package name</dt><dd>{{ viewModel.packageSchema.packageName }}</dd></div>
        <div class="tbi-dl__row"><dt>Version</dt><dd>{{ viewModel.packageSchema.version }}</dd></div>
        <div class="tbi-dl__row"><dt>Publisher</dt><dd>{{ viewModel.packageSchema.publisher }}</dd></div>
        <div class="tbi-dl__row"><dt>Manifest version</dt><dd>{{ viewModel.packageSchema.manifestVersion }}</dd></div>
        <div class="tbi-dl__row"><dt>Capabilities</dt><dd>{{ viewModel.packageSchema.capabilities.join(', ') }}</dd></div>
        <div class="tbi-dl__row"><dt>Permissions</dt><dd>{{ viewModel.packageSchema.permissions.join(', ') }}</dd></div>
        <div class="tbi-dl__row"><dt>Entrypoints</dt><dd>{{ viewModel.packageSchema.entrypoints.join(', ') }}</dd></div>
        <div class="tbi-dl__row"><dt>Signature algorithm</dt><dd>{{ viewModel.packageSchema.signatureAlgorithm }}</dd></div>
        <div class="tbi-dl__row"><dt>Checksum</dt><dd>{{ viewModel.packageSchema.checksum }}</dd></div>
        <div class="tbi-dl__row"><dt>Registry source</dt><dd>{{ viewModel.packageSchema.registrySource }}</dd></div>
      </dl>
    </div>

    <!-- 5. Signature verification panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-signature">
      <h3>Signature verification</h3>
      <p class="tbi-muted">
        The verifier interface is implemented, but the production verifier is NOT
        authorized. A deterministic fixture verifier exists for tests only.
        Unsigned, forged, marketplace, and unknown-publisher inputs are rejected.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Verifier interface</dt><dd>{{ viewModel.signatureVerification.verifierInterfaceImplemented ? 'implemented' : 'missing' }}</dd></div>
        <div class="tbi-dl__row"><dt>Production verifier authorized</dt><dd :data-prod-verifier="viewModel.signatureVerification.productionVerifierAuthorized">{{ viewModel.signatureVerification.productionVerifierAuthorized }}</dd></div>
        <div class="tbi-dl__row"><dt>Fixture verifier only</dt><dd>{{ viewModel.signatureVerification.fixtureVerifierOnly }}</dd></div>
        <div class="tbi-dl__row"><dt>Trusted</dt><dd :data-trusted="viewModel.signatureVerification.trusted">{{ viewModel.signatureVerification.trusted }}</dd></div>
        <div class="tbi-dl__row"><dt>Unsigned rejected</dt><dd :data-unsigned-rejected="viewModel.signatureVerification.unsignedRejected">{{ viewModel.signatureVerification.unsignedRejected }}</dd></div>
        <div class="tbi-dl__row"><dt>Forged rejected</dt><dd :data-forged-rejected="viewModel.signatureVerification.forgedRejected">{{ viewModel.signatureVerification.forgedRejected }}</dd></div>
        <div class="tbi-dl__row"><dt>Production authorization</dt><dd :data-sig-prod-auth="viewModel.signatureVerification.productionAuthorization">{{ viewModel.signatureVerification.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 6. Permission model matrix + capability model -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-permission">
      <h3>Permission model</h3>
      <p class="tbi-muted">
        Every permission is <strong>denied by default</strong>. None is granted,
        no matter what renders or what untrusted metadata a request carries.
        Capabilities are non-executable metadata.
      </p>
      <div class="tbi-board-scroll" role="region" aria-label="Target B permission model" tabindex="0">
        <table class="tbi-board" data-testid="governance-hub-target-b-impl-permission-table">
          <caption class="tbi-board__caption">
            Target B permissions (read-only). Every status is DENIED_BY_DEFAULT.
          </caption>
          <thead>
            <tr>
              <th scope="col">Permission</th>
              <th scope="col">Label</th>
              <th scope="col">Risk</th>
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
              <td><span :data-risk="p.risk">{{ p.risk }}</span></td>
              <td><span class="tbi-board__verdict" :data-permission-status="p.currentStatus"><ShieldX :size="12" aria-hidden="true" /> {{ p.currentStatus }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <ul class="tbi-tags tbi-tags--ok" data-testid="governance-hub-target-b-impl-capabilities">
        <li v-for="c in viewModel.capabilityModel.entries" :key="c.key" :data-capability-key="c.key">
          <ShieldCheck :size="12" aria-hidden="true" /> {{ c.label }} (non-executable)
        </li>
      </ul>
    </div>

    <!-- 7. Registry trust panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-registry">
      <h3>Registry trust policy</h3>
      <p class="tbi-muted">
        The registry is <strong>DISABLED</strong>. Network is off, fetch is off,
        the marketplace is off, unsigned is disallowed, and no publisher is
        trusted. The example URL uses a reserved <code>.invalid</code> domain.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Registry mode</dt><dd :data-registry-mode="viewModel.registryTrust.registryMode">{{ viewModel.registryTrust.registryMode }}</dd></div>
        <div class="tbi-dl__row"><dt>Network enabled</dt><dd :data-registry-network="viewModel.registryTrust.networkEnabled">{{ viewModel.registryTrust.networkEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Fetch enabled</dt><dd :data-registry-fetch="viewModel.registryTrust.fetchEnabled">{{ viewModel.registryTrust.fetchEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Marketplace enabled</dt><dd :data-marketplace-enabled="viewModel.registryTrust.marketplaceEnabled">{{ viewModel.registryTrust.marketplaceEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Trusted publishers</dt><dd>{{ viewModel.registryTrust.trustedPublishersCount }}</dd></div>
        <div class="tbi-dl__row"><dt>Production authorization</dt><dd>{{ viewModel.registryTrust.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 8. Sandbox broker panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-sandbox">
      <h3>Sandbox broker</h3>
      <p class="tbi-muted">
        The broker interface is implemented, but the broker is <strong>disabled</strong>.
        No process spawn, no network, no filesystem write, no secrets.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Broker interface</dt><dd>{{ viewModel.sandboxBroker.brokerInterfaceImplemented ? 'implemented' : 'missing' }}</dd></div>
        <div class="tbi-dl__row"><dt>Broker enabled</dt><dd :data-broker-enabled="viewModel.sandboxBroker.brokerEnabled">{{ viewModel.sandboxBroker.brokerEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Execution allowed</dt><dd :data-sandbox-execution="viewModel.sandboxBroker.executionAllowed">{{ viewModel.sandboxBroker.executionAllowed }}</dd></div>
        <div class="tbi-dl__row"><dt>Process spawn</dt><dd :data-process-spawn="viewModel.sandboxBroker.processSpawnAllowed">{{ viewModel.sandboxBroker.processSpawnAllowed }}</dd></div>
        <div class="tbi-dl__row"><dt>Network</dt><dd :data-sandbox-network="viewModel.sandboxBroker.networkAllowed">{{ viewModel.sandboxBroker.networkAllowed }}</dd></div>
        <div class="tbi-dl__row"><dt>Filesystem write</dt><dd :data-fs-write="viewModel.sandboxBroker.filesystemWriteAllowed">{{ viewModel.sandboxBroker.filesystemWriteAllowed }}</dd></div>
        <div class="tbi-dl__row"><dt>Secrets</dt><dd :data-sandbox-secrets="viewModel.sandboxBroker.secretsAllowed">{{ viewModel.sandboxBroker.secretsAllowed }}</dd></div>
      </dl>
    </div>

    <!-- 9. Approval / authorization gate panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-approval">
      <h3>Approval / authorization gate</h3>
      <p class="tbi-muted">
        Human approval is required and no trust token is provisioned. Fake, AI,
        and metadata approval are all rejected. Production authorization stays
        NO-GO.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Human approval required</dt><dd :data-human-approval-required="viewModel.approvalGate.humanApprovalRequired">{{ viewModel.approvalGate.humanApprovalRequired }}</dd></div>
        <div class="tbi-dl__row"><dt>Trust token provisioned</dt><dd :data-trust-token-provisioned="viewModel.approvalGate.trustTokenProvisioned">{{ viewModel.approvalGate.trustTokenProvisioned }}</dd></div>
        <div class="tbi-dl__row"><dt>Fake approval accepted</dt><dd :data-fake-approval-accepted="viewModel.approvalGate.fakeApprovalAccepted">{{ viewModel.approvalGate.fakeApprovalAccepted }}</dd></div>
        <div class="tbi-dl__row"><dt>AI approval accepted</dt><dd :data-ai-approval-accepted="viewModel.approvalGate.aiApprovalAccepted">{{ viewModel.approvalGate.aiApprovalAccepted }}</dd></div>
        <div class="tbi-dl__row"><dt>Metadata approval accepted</dt><dd :data-metadata-approval-accepted="viewModel.approvalGate.metadataApprovalAccepted">{{ viewModel.approvalGate.metadataApprovalAccepted }}</dd></div>
        <div class="tbi-dl__row"><dt>Production authorization</dt><dd :data-approval-prod-auth="viewModel.approvalGate.productionAuthorization">{{ viewModel.approvalGate.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 10. Execution policy panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-execution-policy">
      <h3>Execution policy</h3>
      <p class="tbi-muted">
        The unified execution policy aggregates every layer. Execution is allowed
        only when all gates pass — today none does. There is no execute button,
        no run button, and no submit control.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Allowed</dt><dd :data-policy-allowed="viewModel.executionPolicy.allowed">{{ viewModel.executionPolicy.allowed }}</dd></div>
        <div class="tbi-dl__row"><dt>Can execute plugin</dt><dd :data-can-execute="viewModel.executionPolicy.canExecutePlugin">{{ viewModel.executionPolicy.canExecutePlugin }}</dd></div>
        <div class="tbi-dl__row"><dt>Can load package</dt><dd :data-can-load="viewModel.executionPolicy.canLoadPluginPackage">{{ viewModel.executionPolicy.canLoadPluginPackage }}</dd></div>
        <div class="tbi-dl__row"><dt>Can fetch registry</dt><dd :data-can-fetch="viewModel.executionPolicy.canFetchRegistry">{{ viewModel.executionPolicy.canFetchRegistry }}</dd></div>
        <div class="tbi-dl__row"><dt>WebUI execute enabled</dt><dd :data-webui-execute="viewModel.executionPolicy.webuiExecuteEnabled">{{ viewModel.executionPolicy.webuiExecuteEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Runtime route enabled</dt><dd :data-runtime-route="viewModel.executionPolicy.runtimeRouteEnabled">{{ viewModel.executionPolicy.runtimeRouteEnabled }}</dd></div>
        <div class="tbi-dl__row"><dt>Production runtime enabled</dt><dd :data-prod-runtime="viewModel.executionPolicy.productionRuntimeEnabled">{{ viewModel.executionPolicy.productionRuntimeEnabled }}</dd></div>
      </dl>
      <ul class="tbi-blockers" data-testid="governance-hub-target-b-impl-policy-reasons">
        <li v-for="reason in viewModel.executionPolicy.reasons" :key="reason" :data-policy-reason="reason">
          <ShieldX :size="13" aria-hidden="true" />
          <span>{{ reason }}</span>
        </li>
      </ul>
    </div>

    <!-- 11. Audit / rollback panel -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-audit-rollback">
      <h3>Audit / rollback</h3>
      <p class="tbi-muted">
        The audit trail is in-memory only — nothing is persisted. The kill switch
        is design-ready only; production rollback is not authorized; production
        rollout stays NO-GO; the production gateway is untouched.
      </p>
      <dl class="tbi-dl">
        <div class="tbi-dl__row"><dt>Audit persistence</dt><dd :data-audit-persistence="viewModel.auditRollback.auditPersistence">{{ viewModel.auditRollback.auditPersistence }}</dd></div>
        <div class="tbi-dl__row"><dt>Audit persisted</dt><dd :data-audit-persisted="viewModel.auditRollback.auditPersisted">{{ viewModel.auditRollback.auditPersisted }}</dd></div>
        <div class="tbi-dl__row"><dt>Kill switch</dt><dd :data-kill-switch="viewModel.auditRollback.killSwitchReady">{{ viewModel.auditRollback.killSwitchReady }}</dd></div>
        <div class="tbi-dl__row"><dt>Production rollback authorized</dt><dd :data-prod-rollback="viewModel.auditRollback.productionRollbackAuthorized">{{ viewModel.auditRollback.productionRollbackAuthorized }}</dd></div>
        <div class="tbi-dl__row"><dt>Production rollout</dt><dd :data-prod-rollout="viewModel.auditRollback.productionRollout">{{ viewModel.auditRollback.productionRollout }}</dd></div>
        <div class="tbi-dl__row"><dt>Production gateway untouched</dt><dd :data-gateway-untouched="viewModel.auditRollback.productionGatewayUntouched">{{ viewModel.auditRollback.productionGatewayUntouched }}</dd></div>
      </dl>
    </div>

    <!-- 12. Enablement blockers -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-blockers">
      <h3>Enablement blockers</h3>
      <p class="tbi-muted">
        What must be completed before Target B could even be considered. Every
        blocker stays unresolved.
      </p>
      <ul class="tbi-blockers">
        <li
          v-for="b in viewModel.enablementBlockers"
          :key="b.key"
          :data-blocker-key="b.key"
          :data-blocker-resolved="b.resolved"
        >
          <Lock :size="13" aria-hidden="true" />
          <div>
            <span class="tbi-blockers__label">{{ b.label }}</span>
            <span class="tbi-blockers__detail">{{ b.detail }}</span>
          </div>
        </li>
      </ul>
      <div class="tbi-rel__links">
        <button
          type="button"
          class="tbi-board__link"
          data-testid="governance-hub-target-b-impl-view-runtime-governance"
          aria-label="View Runtime Governance section"
          @click="onNavigate('runtimeGovernance')"
        >
          View Runtime Governance
        </button>
        <button
          type="button"
          class="tbi-board__link"
          data-testid="governance-hub-target-b-impl-view-human-review"
          aria-label="View Human Review section"
          @click="onNavigate('humanReview')"
        >
          View Human Review
        </button>
      </div>
    </div>

    <!-- 13. Allowed / forbidden action panels -->
    <div class="tbi-block" data-testid="governance-hub-target-b-impl-actions">
      <h3>What this region can and cannot do</h3>
      <div class="tbi-actions">
        <div class="tbi-actions__group">
          <h4>Allowed (read-only)</h4>
          <ul class="tbi-tags tbi-tags--ok" data-testid="governance-hub-target-b-impl-allowed-actions">
            <li v-for="action in viewModel.allowedUiActions" :key="action" :data-allowed-action="action">{{ action }}</li>
          </ul>
        </div>
        <div class="tbi-actions__group">
          <h4>Forbidden (never offered)</h4>
          <ul class="tbi-tags tbi-tags--ban" data-testid="governance-hub-target-b-impl-forbidden-actions">
            <li v-for="action in viewModel.forbiddenActions" :key="action" :data-forbidden-action="action">{{ action }}</li>
          </ul>
        </div>
      </div>
    </div>

    <p class="tbi-muted target-b-impl__footer">
      This region is a gated implementation scaffold. It is not an authorization,
      not an approval, not a signoff, not a closeout, and not production
      authorization. Production plugin runtime, arbitrary plugin loading, remote
      registry, marketplace, external network, real API keys, WebUI execution,
      approval / authorization, and production rollout all remain NO-GO /
      disabled.
    </p>
  </section>
</template>

<style scoped>
.target-b-impl {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.target-b-impl__header h2 {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-impl__header p {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-impl__footer {
  margin-top: var(--space-1, 4px);
}
.tbi-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.tbi-sr-only {
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
.tbi-status-badges {
  list-style: none;
  margin: var(--space-2, 8px) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.tbi-status-badge {
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
.tbi-copy-btn,
.tbi-filter-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.tbi-filter-btn {
  font-weight: 600;
}
.tbi-filter-btn[data-filter-active='true'] {
  border-color: var(--color-accent, #6f8cff);
  color: var(--color-accent, #6f8cff);
}
.tbi-copy-btn:hover,
.tbi-filter-btn:hover,
.tbi-board__link:hover {
  border-color: var(--color-accent, #6f8cff);
}
.tbi-copy-btn:focus-visible,
.tbi-filter-btn:focus-visible,
.tbi-board__link:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.tbi-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.tbi-banner__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  color: var(--color-success, #6ec48e);
  font-weight: 700;
  font-size: var(--font-size-base, 15px);
}
.tbi-banner__lines {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tbi-banner__lines li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text, #e6e6ec);
}
.tbi-block h3 {
  margin: 0 0 var(--space-2, 8px);
}
.tbi-block p.tbi-muted {
  margin: 0 0 var(--space-2, 8px);
}
.tbi-filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.tbi-board-scroll {
  overflow-x: auto;
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
}
.tbi-board {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  min-width: 760px;
}
.tbi-board__caption {
  text-align: left;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
}
.tbi-board th,
.tbi-board td {
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-bottom: 1px solid var(--color-border, #2a2a33);
  vertical-align: top;
}
.tbi-board thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
  font-size: var(--font-size-xs, 12px);
}
.tbi-board__name {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.tbi-board__status {
  font-weight: 600;
}
.tbi-board__status--muted {
  color: var(--color-text-muted, #8a8a94);
}
.tbi-board__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  color: var(--color-danger, #e0566a);
  font-weight: 600;
}
.tbi-board__detail {
  background: var(--color-surface, #101015);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.6;
}
.tbi-board__link {
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
.tbi-tags {
  list-style: none;
  margin: 0 0 var(--space-2, 8px);
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.tbi-tags li {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.tbi-tags--ok li {
  color: var(--color-success, #6ec48e);
}
.tbi-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
.tbi-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tbi-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.tbi-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.tbi-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  text-align: right;
  word-break: break-word;
}
.tbi-blockers {
  list-style: none;
  margin: var(--space-2, 8px) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tbi-blockers li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
  color: var(--color-danger, #e0566a);
}
.tbi-blockers__label {
  display: block;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  font-weight: 600;
}
.tbi-blockers__detail {
  display: block;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.tbi-rel__links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-top: var(--space-2, 8px);
}
.tbi-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.tbi-actions__group h4 {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
</style>
