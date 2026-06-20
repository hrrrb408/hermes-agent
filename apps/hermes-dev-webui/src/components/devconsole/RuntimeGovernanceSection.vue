<script setup lang="ts">
/**
 * Dev Console → Runtime Governance section (Phase 3J).
 *
 * A read-only WebUI surface over the Phase 3I dev-only descriptor-backed
 * fixture runtime. It projects — from frozen static data only — the
 * reviewed-fixture descriptor registry, the registry→runtime binding detail,
 * the supported fixture allowlist, the conservative P0 evidence summary, the
 * frozen no-side-effect surface, the authorization boundary, and the CLI
 * command examples.
 *
 * It performs NO execution, NO plugin loading, NO route change, NO file or
 * network access, and NO production access. There is no Run / Execute / Batch /
 * Approve / Authorize / Enable / Load / Upload / Fetch control, no API-key
 * input, no secret input, no file picker, and no JSON execution input. The
 * only controls are harmless UI-only selects: choosing a descriptor to inspect
 * and toggling a denied-state preview.
 *
 * No new HTTP route is introduced: this is a client-side section inside the
 * existing /console view, served by already-approved static data.
 */
import { computed, ref } from 'vue'
import RuntimeBoundaryBanner from './RuntimeBoundaryBanner.vue'
import RuntimeDescriptorTable from './RuntimeDescriptorTable.vue'
import RuntimeDescriptorDetail from './RuntimeDescriptorDetail.vue'
import RuntimeP0EvidencePanel from './RuntimeP0EvidencePanel.vue'
import RuntimeSafetyMatrix from './RuntimeSafetyMatrix.vue'
import RuntimeCliExamples from './RuntimeCliExamples.vue'
import PluginRuntimeDisabledBanner from './PluginRuntimeDisabledBanner.vue'
import StatusSummaryCards from './StatusSummaryCards.vue'
import {
  buildRuntimeGovernanceViewModel,
  buildSummaryCards,
  buildDescriptorBindingDetail,
  DEFAULT_DESCRIPTOR_ID,
} from '@/lib/runtimeGovernanceViewModel'

const viewModel = buildRuntimeGovernanceViewModel()
const summaryCards = buildSummaryCards()

/** Harmless UI-only state: which descriptor's read-only binding to inspect. */
const selectedDescriptorId = ref<string>(DEFAULT_DESCRIPTOR_ID)
/** Harmless UI-only state: preview the denied-binding state for an unknown id. */
const deniedPreview = ref(false)

const binding = computed(() =>
  deniedPreview.value ? null : buildDescriptorBindingDetail(selectedDescriptorId.value),
)

const fixtureAllowlistPairs = computed(() =>
  viewModel.fixtureAllowlist.map((f) => `${f.pluginId} / ${f.operation}`),
)

function onSelect(descriptorId: string): void {
  deniedPreview.value = false
  selectedDescriptorId.value = descriptorId
}

function toggleDeniedPreview(): void {
  deniedPreview.value = !deniedPreview.value
}
</script>

<template>
  <section
    class="devconsole-section"
    aria-label="Runtime Governance"
    data-testid="runtime-governance-section"
  >
    <div class="devconsole-section__intro">
      <h2>Runtime Governance</h2>
      <p>
        A read-only projection of the Phase 3I dev-only descriptor-backed fixture
        runtime. It <strong>displays only — it does not execute a runtime, does
        not load a plugin, does not authorize production, and does not add a
        backend route</strong>. Every descriptor is dev-only, fixture-only, and
        reviewed-fixture; every authorization verdict is frozen NO-GO /
        not-authorized; every side-effect flag is frozen false.
      </p>
    </div>

    <RuntimeBoundaryBanner :verdicts="viewModel.authorizationVerdicts" />

    <PluginRuntimeDisabledBanner />

    <StatusSummaryCards :cards="summaryCards" />

    <RuntimeDescriptorTable
      :descriptors="viewModel.descriptors"
      :selected-id="deniedPreview ? null : selectedDescriptorId"
      @select="onSelect"
    />

    <div class="devconsole-card rtgov-detail-wrap">
      <div class="rtgov-detail-wrap__bar">
        <h3 style="margin: 0">Descriptor binding detail</h3>
        <button
          type="button"
          class="rtgov-inspect-btn"
          :aria-pressed="deniedPreview"
          data-testid="runtime-denied-preview-toggle"
          @click="toggleDeniedPreview"
        >
          {{ deniedPreview ? 'Show selected binding' : 'Preview denied state' }}
        </button>
      </div>
      <RuntimeDescriptorDetail
        :binding="binding"
        :denied="deniedPreview"
        :denial-reasons="['descriptor_not_in_static_registry', 'descriptor_registry_lookup']"
      />
    </div>

    <div class="devconsole-card" data-testid="runtime-fixture-allowlist">
      <h3>Supported fixture runtime (allowlist)</h3>
      <p class="rtgov-muted">
        The dev-only fixture functions a reviewed descriptor may bind to. Each is
        a pure in-process fixture — never a real plugin, never loaded from disk,
        never fetched remotely. The WebUI does not execute them.
      </p>
      <ul class="rtgov-allowlist" data-testid="runtime-fixture-allowlist-list">
        <li v-for="pair in fixtureAllowlistPairs" :key="pair">
          <code>{{ pair }}</code>
        </li>
      </ul>
    </div>

    <RuntimeP0EvidencePanel :evidence="viewModel.p0Evidence" />

    <RuntimeSafetyMatrix :flags="viewModel.sideEffectFlags" />

    <div class="devconsole-card" data-testid="runtime-route-governance">
      <h3>Route governance status</h3>
      <dl class="rtgov-dl">
        <div class="rtgov-dl__row">
          <dt>Frozen baseline</dt>
          <dd><code>{{ viewModel.routeGovernanceBaseline }}</code></dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>Shape</dt>
          <dd>OpenAPI / Runtime / Tool GET / Tool write / dry-run / execute</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>Backend routes changed</dt>
          <dd :data-flag="`backendRoutesChanged-${viewModel.backendRoutesChanged}`">
            {{ viewModel.backendRoutesChanged ? 'yes' : 'no' }}
          </dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>New HTTP route</dt>
          <dd>0</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>New runtime / plugin route</dt>
          <dd>0</dd>
        </div>
      </dl>
      <p class="rtgov-muted">
        No backend route was added for this section. It is a client-side view
        inside the existing /console page.
      </p>
    </div>

    <RuntimeCliExamples :examples="viewModel.cliExamples" />
  </section>
</template>

<style scoped>
.rtgov-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-detail-wrap {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.rtgov-detail-wrap__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
  flex-wrap: wrap;
}
.rtgov-inspect-btn {
  border: 1px solid var(--color-border, #2a2a33);
  background: transparent;
  color: var(--color-text, #e6e6ec);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-xs, 12px);
  cursor: pointer;
}
.rtgov-inspect-btn:hover {
  border-color: var(--color-accent, #6f8cff);
}
.rtgov-allowlist {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
}
.rtgov-allowlist li {
  border: 1px solid var(--color-border, #2a2a33);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-1, 4px) var(--space-2, 8px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-dl {
  margin: 0 0 var(--space-2, 8px);
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
  text-align: right;
}
</style>
