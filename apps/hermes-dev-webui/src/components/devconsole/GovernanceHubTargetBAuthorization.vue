<script setup lang="ts">
/**
 * Governance Hub → Target B Authorization Package region (Phase 4C).
 *
 * A read-only region inside the Governance Hub that states the **Target B
 * Authorization & Gate Resolution Package**: the validation structure for the
 * real out-of-band authorization materials that Target B would require (a human
 * approval, a trust token, a trusted publisher set, a production signature
 * verifier, a sandbox worker lifecycle, a registry trust policy, a network
 * allowlist, a secret handling policy, a rollback / incident plan, a route
 * authorization, P0 gate resolution, and the enablement readiness evaluator).
 * It does NOT enable any capability and does NOT authorize Target B.
 *
 * It projects, from frozen static data only:
 *   1. an authorization package banner (readiness BLOCKED, execution disabled,
 *      production NO-GO, trust token not provisioned, P0 resolved 0);
 *   2. authorization summary cards;
 *   3. the authorization sub-layer board (11 layers, every one unauthorized);
 *   4. the human approval panel (missing; fake / AI / metadata rejected);
 *   5. the trust token panel (not provisioned; fake token rejected);
 *   6. the trusted publisher panel (empty; unknown / wildcard / marketplace
 *      rejected);
 *   7. the production signature verifier panel (implemented; not authorized;
 *      fixture-only);
 *   8. the sandbox lifecycle panel (not approved; no spawn / network / write /
 *      secrets);
 *   9. the registry / network / secret policy panels (registry disabled;
 *      network allowlist missing; secret policy default deny);
 *  10. the rollback / incident panel (design-ready only; rollout NO-GO);
 *  11. the route authorization panel (not authorized; deltas 0; route counts
 *      unchanged);
 *  12. the P0 gate coverage panel (5 pending gates; resolved delta 0);
 *  13. the enablement readiness panel (BLOCKED; blockers list);
 *  14. the enablement blockers + forbidden / allowed action panels.
 *
 * It performs NO approval, NO authorization, NO signoff, NO resolution, NO
 * override, NO production rollout, NO trust token provisioning, NO execution,
 * NO plugin loading, NO registry fetch, NO marketplace access, NO route change,
 * NO file or network access, and NO production access. There is NO Approve /
 * Reject / Authorize / Sign off / Resolve / Override / Enable / Run / Execute /
 * Provision / Upload / Install / Fetch / Rollout control, NO API-key input, NO
 * secret input, NO trust-token input, NO file picker, NO signature upload, and
 * NO JSON execution input. The only controls are harmless UI-only toggles:
 * filtering the authorization layers, inspecting a layer, viewing the
 * cross-linked regions, and copying a read-only summary.
 *
 * Target B authorization package is NOT production runtime authorized, NOT
 * trust token provisioned, NOT production signature verifier authorized, NOT
 * sandbox lifecycle approved, NOT registry enabled, NOT marketplace enabled,
 * NOT network allowlist approved, NOT secret policy approved, NOT rollback /
 * incident plan approved, NOT route authorized, and NOT P0 resolved. The
 * readiness status stays BLOCKED. P0 resolved stays 0. No new backend route is
 * introduced.
 */
import { computed, ref } from 'vue'
import { Lock, ShieldX } from '@lucide/vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'
import {
  buildTargetBAuthorizationViewModel,
  buildTargetBAuthorizationSummaryText,
  filterTargetBAuthorizationLayers,
  TARGET_B_AUTHORIZATION_LAYER_FILTER_OPTIONS,
} from '@/lib/targetBAuthorizationViewModel'
import type { TargetBAuthorizationLayerFilterKey } from '@/types/api/targetBAuthorization'

const viewModel = buildTargetBAuthorizationViewModel()
const nav = useDevConsoleNavStore()

/** Harmless UI-only state: the active client-side authorization layer filter. */
const layerFilter = ref<TargetBAuthorizationLayerFilterKey>('all')
/** Harmless UI-only state: which authorization layer detail is expanded. */
const expandedLayerKey = ref<string | null>(null)

const filteredLayers = computed(() => filterTargetBAuthorizationLayers(layerFilter.value))

function setFilter(key: TargetBAuthorizationLayerFilterKey): void {
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
  const text = buildTargetBAuthorizationSummaryText()
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
    class="devconsole-card target-b-authz"
    aria-label="Target B Authorization Package (gated)"
    data-testid="governance-hub-target-b-authz-region"
  >
    <header class="target-b-authz__header">
      <h2 data-testid="governance-hub-target-b-authz-heading">
        Target B — Authorization Package (Gated)
      </h2>
      <p class="tba-muted">
        Phase 4C builds the <strong>authorization-material validation structure</strong>
        for the Target B production plugin runtime — the human approval schema, the
        trust token validation pipeline, the trusted publisher set, the production
        signature verifier authorization adapter, the sandbox worker lifecycle
        approval, the registry / network / secret policies, the rollback / incident
        plan, the route authorization plan, the P0 gate resolution evaluator, and the
        enablement readiness evaluator. <strong>Every gate stays fail-closed.</strong>
        Readiness stays BLOCKED, the trust token stays not provisioned, every
        authorization stays NO-GO, and P0 resolved stays 0.
      </p>
      <ul
        class="tba-status-badges"
        data-testid="governance-hub-target-b-authz-status-badges"
        aria-label="Target B authorization status"
      >
        <li
          v-for="badge in viewModel.statusBadges"
          :key="badge.label"
          class="tba-status-badge"
          :data-status-badge="badge.label"
        >
          {{ badge.label }}
        </li>
      </ul>
    </header>

    <!-- 1. Authorization package banner -->
    <div
      class="tba-banner"
      data-testid="governance-hub-target-b-authz-banner"
      role="group"
      aria-label="Target B authorization package status"
    >
      <div class="tba-banner__verdict" data-authz-verdict="BLOCKED">
        <ShieldX :size="16" aria-hidden="true" />
        <span>Target B: AUTHORIZATION PACKAGE (readiness BLOCKED)</span>
      </div>
      <ul class="tba-banner__lines" data-testid="governance-hub-target-b-authz-banner-lines">
        <li data-banner-line="readiness-blocked">Readiness BLOCKED</li>
        <li data-banner-line="execution-disabled">Target B execution disabled</li>
        <li data-banner-line="production-nogo">Production runtime NO-GO</li>
        <li data-banner-line="trust-token-missing">Trust token not provisioned</li>
        <li data-banner-line="p0-zero">P0 resolved 0</li>
        <li data-banner-line="pending-five">Pending human review 5</li>
      </ul>
      <div class="tba-banner__copy">
        <button
          type="button"
          class="tba-copy-btn"
          :data-copy-state="copyState"
          data-testid="governance-hub-target-b-authz-copy-summary"
          @click="onCopySummary"
        >
          {{ copyState === 'copied' ? 'Copied' : copyState === 'unavailable' ? 'Unavailable' : 'Copy Target B authorization summary' }}
        </button>
      </div>
    </div>

    <!-- 2. Authorization summary cards -->
    <h3>Target B authorization package summary</h3>
    <StatusSummaryCards :cards="viewModel.summaryCards" />

    <!-- 3. Authorization sub-layer board -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-layers">
      <h3>Authorization layers</h3>
      <p class="tba-muted">
        Eleven independent authorization sub-layers. Every one is unauthorized
        (one is design-ready only). The status filter is a harmless client-only
        toggle on static data.
      </p>
      <div class="tba-filter" role="group" aria-label="Filter authorization layers">
        <button
          v-for="opt in TARGET_B_AUTHORIZATION_LAYER_FILTER_OPTIONS"
          :key="opt.key"
          type="button"
          class="tba-filter-btn"
          :data-testid="`governance-hub-target-b-authz-layer-filter-${opt.key}`"
          :data-filter-active="layerFilter === opt.key"
          :aria-pressed="layerFilter === opt.key"
          @click="setFilter(opt.key)"
        >
          {{ opt.label }}
        </button>
      </div>
      <div class="tba-board-scroll" role="region" aria-label="Target B authorization layers" tabindex="0">
        <table class="tba-board" data-testid="governance-hub-target-b-authz-layers-table">
          <caption class="tba-board__caption">
            Target B authorization layers (read-only). Columns: layer, status,
            authorized, fixture-only, risk, required material.
          </caption>
          <thead>
            <tr>
              <th scope="col">Layer</th>
              <th scope="col">Status</th>
              <th scope="col">Authorized</th>
              <th scope="col">Fixture-only</th>
              <th scope="col">Risk</th>
              <th scope="col"><span class="tba-sr-only">Inspect</span></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="l in filteredLayers" :key="l.key">
              <tr :data-layer-key="l.key" :data-layer-status="l.status">
                <td><span class="tba-board__name">{{ l.layer }}</span></td>
                <td><span class="tba-board__status tba-board__status--muted" :data-status="l.status">{{ l.status }}</span></td>
                <td><span class="tba-board__verdict" data-authorized="false"><ShieldX :size="12" aria-hidden="true" /> false</span></td>
                <td><span :data-fixture-only="l.fixtureOnly">{{ l.fixtureOnly }}</span></td>
                <td><span :data-risk="l.riskLevel">{{ l.riskLevel }}</span></td>
                <td>
                  <button
                    type="button"
                    class="tba-board__link"
                    :data-testid="`governance-hub-target-b-authz-layer-inspect-${l.key}`"
                    :aria-expanded="expandedLayerKey === l.key"
                    aria-label="Inspect layer details"
                    @click="toggleInspect(l.key)"
                  >
                    Inspect
                  </button>
                </td>
              </tr>
              <tr v-if="expandedLayerKey === l.key" :data-layer-detail="l.key">
                <td colspan="6" class="tba-board__detail">
                  <p><strong>Required material:</strong> {{ l.requiredMaterial }}</p>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 4. Human approval panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-human-approval">
      <h3>Human approval</h3>
      <p class="tba-muted">
        No real out-of-band human approval exists. Fake, AI, metadata, and
        static-manifest approvals are all rejected. A fixture approval is never
        production authorization.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Approval present</dt><dd :data-approval-present="viewModel.humanApproval.approvalPresent">{{ viewModel.humanApproval.approvalPresent }}</dd></div>
        <div class="tba-dl__row"><dt>Valid</dt><dd :data-approval-valid="viewModel.humanApproval.valid">{{ viewModel.humanApproval.valid }}</dd></div>
        <div class="tba-dl__row"><dt>Fake approval rejected</dt><dd :data-fake-rejected="viewModel.humanApproval.fakeApprovalRejected">{{ viewModel.humanApproval.fakeApprovalRejected }}</dd></div>
        <div class="tba-dl__row"><dt>AI approval rejected</dt><dd :data-ai-rejected="viewModel.humanApproval.aiApprovalRejected">{{ viewModel.humanApproval.aiApprovalRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Metadata approval rejected</dt><dd :data-metadata-rejected="viewModel.humanApproval.metadataApprovalRejected">{{ viewModel.humanApproval.metadataApprovalRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Required gate coverage</dt><dd>{{ viewModel.humanApproval.requiredGateCoverage.join(', ') }}</dd></div>
        <div class="tba-dl__row"><dt>Production authorization</dt><dd :data-approval-prod-auth="viewModel.humanApproval.productionAuthorization">{{ viewModel.humanApproval.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 5. Trust token panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-trust-token">
      <h3>Trust token</h3>
      <p class="tba-muted">
        No trust token is provisioned. A smuggled fake token is rejected. No
        secret is read and no production home is accessed.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Provisioned</dt><dd :data-token-provisioned="viewModel.trustToken.provisioned">{{ viewModel.trustToken.provisioned }}</dd></div>
        <div class="tba-dl__row"><dt>Valid</dt><dd :data-token-valid="viewModel.trustToken.valid">{{ viewModel.trustToken.valid }}</dd></div>
        <div class="tba-dl__row"><dt>Fake token rejected</dt><dd :data-fake-token-rejected="viewModel.trustToken.fakeTokenRejected">{{ viewModel.trustToken.fakeTokenRejected }}</dd></div>
        <div class="tba-dl__row"><dt>No secret read</dt><dd :data-no-secret-read="viewModel.trustToken.noSecretRead">{{ viewModel.trustToken.noSecretRead }}</dd></div>
        <div class="tba-dl__row"><dt>No production home access</dt><dd :data-no-prod-home="viewModel.trustToken.noProductionHomeAccess">{{ viewModel.trustToken.noProductionHomeAccess }}</dd></div>
        <div class="tba-dl__row"><dt>Production authorization</dt><dd :data-token-prod-auth="viewModel.trustToken.productionAuthorization">{{ viewModel.trustToken.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 6. Trusted publisher panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-trusted-publishers">
      <h3>Trusted publishers</h3>
      <p class="tba-muted">
        The production trusted publisher set is empty. Unknown, marketplace,
        unsigned, wildcard, and overbroad publishers are rejected.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Trusted publishers</dt><dd :data-publishers-count="viewModel.trustedPublishers.trustedPublishersCount">{{ viewModel.trustedPublishers.trustedPublishersCount }}</dd></div>
        <div class="tba-dl__row"><dt>Unknown rejected</dt><dd :data-unknown-rejected="viewModel.trustedPublishers.unknownPublisherRejected">{{ viewModel.trustedPublishers.unknownPublisherRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Wildcard rejected</dt><dd :data-wildcard-rejected="viewModel.trustedPublishers.wildcardPublisherRejected">{{ viewModel.trustedPublishers.wildcardPublisherRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Marketplace rejected</dt><dd :data-marketplace-pub-rejected="viewModel.trustedPublishers.marketplacePublisherRejected">{{ viewModel.trustedPublishers.marketplacePublisherRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Production authorization</dt><dd>{{ viewModel.trustedPublishers.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 7. Production signature verifier panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-production-signature">
      <h3>Production signature verifier</h3>
      <p class="tba-muted">
        The verifier interface is implemented, but the production verifier is NOT
        authorized. The fixture verifier is test-only. A valid fixture signature
        does not imply production authorization.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Verifier interface</dt><dd>{{ viewModel.productionSignature.verifierInterfaceImplemented ? 'implemented' : 'missing' }}</dd></div>
        <div class="tba-dl__row"><dt>Production verifier authorized</dt><dd :data-prod-verifier="viewModel.productionSignature.productionVerifierAuthorized">{{ viewModel.productionSignature.productionVerifierAuthorized }}</dd></div>
        <div class="tba-dl__row"><dt>Fixture verifier only</dt><dd :data-fixture-only="viewModel.productionSignature.fixtureVerifierOnly">{{ viewModel.productionSignature.fixtureVerifierOnly }}</dd></div>
        <div class="tba-dl__row"><dt>Forged rejected</dt><dd :data-forged-rejected="viewModel.productionSignature.forgedSignatureRejected">{{ viewModel.productionSignature.forgedSignatureRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Unknown publisher rejected</dt><dd :data-sig-unknown-rejected="viewModel.productionSignature.unknownPublisherRejected">{{ viewModel.productionSignature.unknownPublisherRejected }}</dd></div>
        <div class="tba-dl__row"><dt>Production authorization</dt><dd :data-sig-prod-auth="viewModel.productionSignature.productionAuthorization">{{ viewModel.productionSignature.productionAuthorization }}</dd></div>
      </dl>
    </div>

    <!-- 8. Sandbox lifecycle panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-sandbox">
      <h3>Sandbox worker lifecycle</h3>
      <p class="tba-muted">
        The worker lifecycle is not approved. No worker start, no process spawn,
        no network, no filesystem write, no secrets. The production gateway is
        untouched.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Lifecycle approved</dt><dd :data-lifecycle-approved="viewModel.sandboxLifecycle.lifecycleApproved">{{ viewModel.sandboxLifecycle.lifecycleApproved }}</dd></div>
        <div class="tba-dl__row"><dt>Worker start</dt><dd :data-worker-start="viewModel.sandboxLifecycle.workerStartAllowed">{{ viewModel.sandboxLifecycle.workerStartAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Process spawn</dt><dd :data-sbx-spawn="viewModel.sandboxLifecycle.processSpawnAllowed">{{ viewModel.sandboxLifecycle.processSpawnAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Network</dt><dd :data-sbx-network="viewModel.sandboxLifecycle.networkAllowed">{{ viewModel.sandboxLifecycle.networkAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Filesystem write</dt><dd :data-sbx-write="viewModel.sandboxLifecycle.filesystemWriteAllowed">{{ viewModel.sandboxLifecycle.filesystemWriteAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Secrets</dt><dd :data-sbx-secrets="viewModel.sandboxLifecycle.secretsAllowed">{{ viewModel.sandboxLifecycle.secretsAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Gateway untouched</dt><dd :data-sbx-gateway="viewModel.sandboxLifecycle.productionGatewayUntouched">{{ viewModel.sandboxLifecycle.productionGatewayUntouched }}</dd></div>
      </dl>
    </div>

    <!-- 9. Registry / network / secret policy panels -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-policies">
      <h3>Registry / network / secret policies</h3>
      <p class="tba-muted">
        The registry is disabled; the network allowlist is missing (default deny);
        the secret handling policy is default-deny. No fetch, no marketplace, no
        socket, no secret read.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Registry disabled</dt><dd :data-registry-disabled="viewModel.policies.registryDisabled">{{ viewModel.policies.registryDisabled }}</dd></div>
        <div class="tba-dl__row"><dt>Registry fetch</dt><dd :data-registry-fetch="viewModel.policies.registryFetchAllowed">{{ viewModel.policies.registryFetchAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Marketplace</dt><dd :data-policy-marketplace="viewModel.policies.marketplaceAllowed">{{ viewModel.policies.marketplaceAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>Network allowlist present</dt><dd :data-network-allowlist="viewModel.policies.networkAllowlistPresent">{{ viewModel.policies.networkAllowlistPresent }}</dd></div>
        <div class="tba-dl__row"><dt>Destinations allowed</dt><dd :data-destinations="viewModel.policies.networkDestinationsAllowed">{{ viewModel.policies.networkDestinationsAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>No socket opened</dt><dd :data-no-socket="viewModel.policies.noSocketOpened">{{ viewModel.policies.noSocketOpened }}</dd></div>
        <div class="tba-dl__row"><dt>Secret policy</dt><dd :data-secret-policy="viewModel.policies.secretPolicyDefaultDeny">{{ viewModel.policies.secretPolicyDefaultDeny ? 'default deny' : 'allowed' }}</dd></div>
        <div class="tba-dl__row"><dt>No secret read</dt><dd :data-no-secret-read="viewModel.policies.noSecretRead">{{ viewModel.policies.noSecretRead }}</dd></div>
      </dl>
    </div>

    <!-- 10. Rollback / incident panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-rollback">
      <h3>Rollback / incident plan</h3>
      <p class="tba-muted">
        The rollback plan is design-only; the incident plan is not approved; the
        kill switch is design-ready only. Production rollback is not authorized
        and production rollout stays NO-GO.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Rollback plan approved</dt><dd :data-rollback-approved="viewModel.rollbackIncident.rollbackPlanApproved">{{ viewModel.rollbackIncident.rollbackPlanApproved }}</dd></div>
        <div class="tba-dl__row"><dt>Incident plan approved</dt><dd :data-incident-approved="viewModel.rollbackIncident.incidentPlanApproved">{{ viewModel.rollbackIncident.incidentPlanApproved }}</dd></div>
        <div class="tba-dl__row"><dt>Kill switch</dt><dd :data-kill-switch="viewModel.rollbackIncident.killSwitchReady">{{ viewModel.rollbackIncident.killSwitchReady }}</dd></div>
        <div class="tba-dl__row"><dt>Production rollout</dt><dd :data-rollout="viewModel.rollbackIncident.productionRollout">{{ viewModel.rollbackIncident.productionRollout }}</dd></div>
        <div class="tba-dl__row"><dt>Gateway untouched</dt><dd :data-rb-gateway="viewModel.rollbackIncident.productionGatewayUntouched">{{ viewModel.rollbackIncident.productionGatewayUntouched }}</dd></div>
      </dl>
    </div>

    <!-- 11. Route authorization panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-route">
      <h3>Route authorization</h3>
      <p class="tba-muted">
        No route is authorized. The proposed routes are disabled documentation
        only. Zero are registered, both deltas are zero, and the route counts are
        unchanged (34/34/5/0/1/1).
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Route authorized</dt><dd :data-route-authorized="viewModel.routeAuthorization.routeAuthorized">{{ viewModel.routeAuthorization.routeAuthorized }}</dd></div>
        <div class="tba-dl__row"><dt>Proposed routes registered</dt><dd :data-routes-registered="viewModel.routeAuthorization.proposedRoutesRegistered">{{ viewModel.routeAuthorization.proposedRoutesRegistered }}</dd></div>
        <div class="tba-dl__row"><dt>OpenAPI delta</dt><dd :data-openapi-delta="viewModel.routeAuthorization.openapiDelta">{{ viewModel.routeAuthorization.openapiDelta }}</dd></div>
        <div class="tba-dl__row"><dt>Runtime route delta</dt><dd :data-runtime-delta="viewModel.routeAuthorization.runtimeRouteDelta">{{ viewModel.routeAuthorization.runtimeRouteDelta }}</dd></div>
        <div class="tba-dl__row"><dt>Route baseline</dt><dd :data-route-baseline="viewModel.routeAuthorization.routeGovernanceBaseline">{{ viewModel.routeAuthorization.routeGovernanceBaseline }}</dd></div>
        <div class="tba-dl__row"><dt>Backend routes changed</dt><dd :data-backend-changed="viewModel.routeAuthorization.backendRoutesChanged">{{ viewModel.routeAuthorization.backendRoutesChanged }}</dd></div>
      </dl>
    </div>

    <!-- 12. P0 gate coverage panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-p0">
      <h3>P0 gate coverage</h3>
      <p class="tba-muted">
        The five pending human-review gates (P0-15 / P0-16 / P0-18 / P0-19 / P0-22)
        remain unresolved. Code evidence alone cannot resolve them; a real human
        approval + trust token + evidence is required.
      </p>
      <div class="tba-board-scroll" role="region" aria-label="Target B P0 gate coverage" tabindex="0">
        <table class="tba-board" data-testid="governance-hub-target-b-authz-p0-table">
          <caption class="tba-board__caption">
            Target B P0 gate coverage (read-only). Every gate is unresolved.
          </caption>
          <thead>
            <tr>
              <th scope="col">Gate</th>
              <th scope="col">Resolved</th>
              <th scope="col">Has evidence</th>
              <th scope="col">Human approval</th>
              <th scope="col">Trust token</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="g in viewModel.p0GateCoverage.coverage"
              :key="g.gateId"
              :data-gate-id="g.gateId"
            >
              <td><code>{{ g.gateId }}</code></td>
              <td><span class="tba-board__verdict" :data-gate-resolved="g.resolved"><ShieldX :size="12" aria-hidden="true" /> {{ g.resolved }}</span></td>
              <td><span :data-gate-evidence="g.hasEvidence">{{ g.hasEvidence }}</span></td>
              <td><span :data-gate-approval="g.hasHumanApproval">{{ g.hasHumanApproval }}</span></td>
              <td><span :data-gate-token="g.hasTrustToken">{{ g.hasTrustToken }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Resolved count delta</dt><dd :data-resolved-delta="viewModel.p0GateCoverage.resolvedCountDelta">{{ viewModel.p0GateCoverage.resolvedCountDelta }}</dd></div>
        <div class="tba-dl__row"><dt>P0 resolved</dt><dd :data-p0-resolved="viewModel.p0GateCoverage.p0Resolved">{{ viewModel.p0GateCoverage.p0Resolved }}</dd></div>
        <div class="tba-dl__row"><dt>Pending human review</dt><dd :data-pending="viewModel.p0GateCoverage.pendingHumanReview">{{ viewModel.p0GateCoverage.pendingHumanReview }}</dd></div>
      </dl>
    </div>

    <!-- 13. Enablement readiness panel -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-readiness">
      <h3>Enablement readiness</h3>
      <p class="tba-muted">
        The unified readiness evaluator composes every authorization sub-layer.
        The default verdict is BLOCKED because no real authorization material
        exists. Production cannot be enabled.
      </p>
      <dl class="tba-dl">
        <div class="tba-dl__row"><dt>Readiness status</dt><dd :data-readiness="viewModel.enablementReadiness.readinessStatus">{{ viewModel.enablementReadiness.readinessStatus }}</dd></div>
        <div class="tba-dl__row"><dt>Production enablement allowed</dt><dd :data-enablement-allowed="viewModel.enablementReadiness.productionEnablementAllowed">{{ viewModel.enablementReadiness.productionEnablementAllowed }}</dd></div>
        <div class="tba-dl__row"><dt>All gates pass</dt><dd :data-all-gates-pass="viewModel.enablementReadiness.allGatesPass">{{ viewModel.enablementReadiness.allGatesPass }}</dd></div>
      </dl>
      <ul class="tba-blockers" data-testid="governance-hub-target-b-authz-readiness-blockers">
        <li v-for="b in viewModel.enablementReadiness.blockers" :key="b" :data-blocker="b">
          <ShieldX :size="13" aria-hidden="true" />
          <span>{{ b }}</span>
        </li>
      </ul>
    </div>

    <!-- 14. Enablement blockers + forbidden / allowed actions -->
    <div class="tba-block" data-testid="governance-hub-target-b-authz-blockers">
      <h3>Enablement blockers</h3>
      <p class="tba-muted">
        What real authorization material must exist before Target B could even be
        considered. Every blocker stays unresolved.
      </p>
      <ul class="tba-blockers">
        <li
          v-for="b in viewModel.enablementBlockers"
          :key="b.key"
          :data-blocker-key="b.key"
          :data-blocker-resolved="b.resolved"
        >
          <Lock :size="13" aria-hidden="true" />
          <div>
            <span class="tba-blockers__label">{{ b.label }}</span>
            <span class="tba-blockers__detail">{{ b.detail }}</span>
          </div>
        </li>
      </ul>
      <div class="tba-rel__links">
        <button
          type="button"
          class="tba-board__link"
          data-testid="governance-hub-target-b-authz-view-runtime-governance"
          aria-label="View Runtime Governance section"
          @click="onNavigate('runtimeGovernance')"
        >
          View Runtime Governance
        </button>
        <button
          type="button"
          class="tba-board__link"
          data-testid="governance-hub-target-b-authz-view-human-review"
          aria-label="View Human Review section"
          @click="onNavigate('humanReview')"
        >
          View Human Review
        </button>
      </div>
    </div>

    <div class="tba-block" data-testid="governance-hub-target-b-authz-actions">
      <h3>What this region can and cannot do</h3>
      <div class="tba-actions">
        <div class="tba-actions__group">
          <h4>Allowed (read-only)</h4>
          <ul class="tba-tags tba-tags--ok" data-testid="governance-hub-target-b-authz-allowed-actions">
            <li v-for="action in viewModel.allowedUiActions" :key="action" :data-allowed-action="action">{{ action }}</li>
          </ul>
        </div>
        <div class="tba-actions__group">
          <h4>Forbidden (never offered)</h4>
          <ul class="tba-tags tba-tags--ban" data-testid="governance-hub-target-b-authz-forbidden-actions">
            <li v-for="action in viewModel.forbiddenActions" :key="action" :data-forbidden-action="action">{{ action }}</li>
          </ul>
        </div>
      </div>
    </div>

    <p class="tba-muted target-b-authz__footer">
      This region is an authorization-material validation structure. It is not an
      authorization, not an approval, not a signoff, not a closeout, not production
      authorization, and not an enablement. No approval is fabricated, no P0 is
      bypassed, no trust token is minted, no production runtime is flipped to GO,
      and no route is authorized. The readiness status stays BLOCKED, the trust
      token stays not provisioned, every authorization stays NO-GO, P0 resolved
      stays 0, and the route baseline stays unchanged (34/34/5/0/1/1).
    </p>
  </section>
</template>

<style scoped>
.target-b-authz {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 16px);
}
.target-b-authz__header h2 {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-authz__header p {
  margin: 0 0 var(--space-2, 8px);
}
.target-b-authz__footer {
  margin-top: var(--space-1, 4px);
}
.tba-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
  line-height: 1.5;
}
.tba-sr-only {
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
.tba-status-badges {
  list-style: none;
  margin: var(--space-2, 8px) 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.tba-status-badge {
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
.tba-copy-btn,
.tba-filter-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.tba-filter-btn {
  font-weight: 600;
}
.tba-filter-btn[data-filter-active='true'] {
  border-color: var(--color-accent, #6f8cff);
  color: var(--color-accent, #6f8cff);
}
.tba-copy-btn:hover,
.tba-filter-btn:hover,
.tba-board__link:hover {
  border-color: var(--color-accent, #6f8cff);
}
.tba-copy-btn:focus-visible,
.tba-filter-btn:focus-visible,
.tba-board__link:focus-visible {
  outline: 2px solid var(--color-accent, #6f8cff);
  outline-offset: 1px;
}
.tba-banner {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-3, 12px);
  background: var(--color-surface, #101015);
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.tba-banner__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2, 8px);
  color: var(--color-danger, #e0566a);
  font-weight: 700;
  font-size: var(--font-size-base, 15px);
}
.tba-banner__lines {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tba-banner__lines li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  color: var(--color-text, #e6e6ec);
}
.tba-block h3 {
  margin: 0 0 var(--space-2, 8px);
}
.tba-block p.tba-muted {
  margin: 0 0 var(--space-2, 8px);
}
.tba-filter {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-bottom: var(--space-2, 8px);
}
.tba-board-scroll {
  overflow-x: auto;
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
}
.tba-board {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm, 13px);
  min-width: 720px;
}
.tba-board__caption {
  text-align: left;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
}
.tba-board th,
.tba-board td {
  text-align: left;
  padding: var(--space-1, 4px) var(--space-2, 8px);
  border-bottom: 1px solid var(--color-border, #2a2a33);
  vertical-align: top;
}
.tba-board thead th {
  color: var(--color-text-muted, #8a8a94);
  font-weight: 600;
  font-size: var(--font-size-xs, 12px);
}
.tba-board__name {
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
}
.tba-board__status {
  font-weight: 600;
}
.tba-board__status--muted {
  color: var(--color-text-muted, #8a8a94);
}
.tba-board__verdict {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  color: var(--color-danger, #e0566a);
  font-weight: 600;
}
.tba-board__detail {
  background: var(--color-surface, #101015);
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.6;
}
.tba-board__link {
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
.tba-dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tba-dl__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.tba-dl__row dt {
  color: var(--color-text-muted, #8a8a94);
}
.tba-dl__row dd {
  margin: 0;
  font-weight: 600;
  color: var(--color-text, #e6e6ec);
  text-align: right;
  word-break: break-word;
}
.tba-blockers {
  list-style: none;
  margin: var(--space-2, 8px) 0 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.tba-blockers li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2, 8px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
  background: var(--color-surface, #101015);
  color: var(--color-danger, #e0566a);
}
.tba-blockers__label {
  display: block;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text, #e6e6ec);
  font-weight: 600;
}
.tba-blockers__detail {
  display: block;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
  line-height: 1.5;
}
.tba-rel__links {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin-top: var(--space-2, 8px);
}
.tba-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--space-3, 12px);
}
.tba-actions__group h4 {
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.tba-tags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1, 4px) var(--space-2, 8px);
}
.tba-tags li {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
}
.tba-tags--ok li {
  color: var(--color-success, #6ec48e);
}
.tba-tags--ban li {
  color: var(--color-text-muted, #8a8a94);
}
</style>
