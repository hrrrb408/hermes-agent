<script setup lang="ts">
/**
 * Runtime Governance descriptor binding detail (Phase 3J).
 *
 * Read-only projection of the registry→runtime binding for the selected
 * descriptor (no execution). Renders three static states:
 *   - binding  : a known reviewed descriptor (bindingAllowed true, no denials)
 *   - denied   : a denied-binding preview (e.g. an unknown / unsafe id)
 *   - empty    : no descriptor selected
 *
 * Every field is read-only text. There is no Run / Execute / Approve / Authorize
 * control. The redacted descriptor preview never leaks a raw payload.
 */
import { computed } from 'vue'
import EmptyState from '@/components/common/EmptyState.vue'
import type { RuntimeDescriptorBindingDetail } from '@/types/api/runtimeGovernance'

const props = defineProps<{
  binding: RuntimeDescriptorBindingDetail | null
  denied?: boolean
  denialReasons?: readonly string[]
}>()

type DetailMode = 'binding' | 'denied' | 'empty'

const mode = computed<DetailMode>(() => {
  if (props.denied) return 'denied'
  if (props.binding) return 'binding'
  return 'empty'
})

const runtimeFlagEntries = computed(() =>
  props.binding
    ? Object.entries(props.binding.runtimeFlags).map(([k, v]) => ({ key: k, value: v }))
    : [],
)
</script>

<template>
  <div class="devconsole-card rtgov-detail" data-testid="runtime-descriptor-detail">
    <h3>Descriptor binding detail</h3>

    <div v-if="mode === 'empty'" data-testid="runtime-detail-empty">
      <EmptyState
        message="No descriptor selected."
        hint="Select “Inspect” on a reviewed fixture descriptor to view its read-only binding."
      />
    </div>

    <div
      v-else-if="mode === 'denied'"
      class="rtgov-detail__denied"
      data-testid="runtime-detail-denied"
      role="status"
    >
      <p><strong>Descriptor binding denied.</strong></p>
      <p class="rtgov-muted">
        An unknown or unsafe descriptor id is not in the static reviewed registry,
        so no fixture runs and no binding is resolved.
      </p>
      <ul class="rtgov-detail__reasons" data-testid="runtime-detail-denial-reasons">
        <li v-for="r in denialReasons ?? ['descriptor_not_in_static_registry']" :key="r">
          <code>{{ r }}</code>
        </li>
      </ul>
    </div>

    <div v-else data-testid="runtime-detail-binding">
      <dl class="rtgov-dl">
        <div class="rtgov-dl__row">
          <dt>descriptorId</dt>
          <dd><code>{{ binding!.descriptorId }}</code></dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>bindingAllowed</dt>
          <dd :data-flag="`bindingAllowed-${binding!.bindingAllowed}`">{{ binding!.bindingAllowed }}</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>source</dt>
          <dd><code>{{ binding!.source }}</code></dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>pluginId</dt>
          <dd><code>{{ binding!.pluginId }}</code></dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>operation</dt>
          <dd><code>{{ binding!.operation }}</code></dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>devOnly</dt>
          <dd>{{ binding!.devOnly }}</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>fixtureOnly</dt>
          <dd>{{ binding!.fixtureOnly }}</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>reviewedFixture</dt>
          <dd>{{ binding!.reviewedFixture }}</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>denialReasons</dt>
          <dd>{{ binding!.denialReasons.length === 0 ? '[]' : binding!.denialReasons.join(', ') }}</dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>triggeredGuards</dt>
          <dd>
            <code v-for="g in binding!.triggeredGuards" :key="g">{{ g }} </code>
          </dd>
        </div>
        <div class="rtgov-dl__row">
          <dt>redactedDescriptor</dt>
          <dd data-testid="runtime-detail-redacted-descriptor">{{
            binding!.redactedDescriptor.redactionApplied ? '{ redactionApplied: true }' : ''
          }}</dd>
        </div>
      </dl>

      <h4 class="rtgov-detail__subhead">Runtime flags (frozen)</h4>
      <ul class="rtgov-detail__flags" data-testid="runtime-detail-runtime-flags">
        <li v-for="f in runtimeFlagEntries" :key="f.key" :data-flag="`${f.key}-${f.value}`">
          <code>{{ f.key }}</code>
          <span :class="f.value ? 'rtgov-flag--true' : 'rtgov-flag--false'">{{ f.value }}</span>
        </li>
      </ul>

      <p class="rtgov-detail__note" data-testid="runtime-detail-read-only-note">
        Read-only projection — source = static_descriptor_registry. The WebUI does
        not execute this binding.
      </p>
    </div>
  </div>
</template>

<style scoped>
.rtgov-detail {
  display: flex;
  flex-direction: column;
  gap: var(--space-2, 8px);
}
.rtgov-muted {
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-dl {
  margin: 0;
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
  word-break: break-all;
}
.rtgov-detail__denied {
  border: 1px solid var(--color-danger, #e0566a);
  border-radius: var(--radius-sm, 6px);
  padding: var(--space-2, 8px) var(--space-3, 12px);
}
.rtgov-detail__reasons {
  margin: var(--space-2, 8px) 0 0;
  padding-left: var(--space-4, 16px);
}
.rtgov-detail__subhead {
  margin: var(--space-2, 8px) 0 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--color-text-muted, #8a8a94);
}
.rtgov-detail__flags {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--space-1, 4px) var(--space-3, 12px);
  font-size: var(--font-size-sm, 13px);
}
.rtgov-detail__flags li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2, 8px);
}
.rtgov-flag--true {
  color: var(--color-success, #6ec48e);
  font-weight: 600;
}
.rtgov-flag--false {
  color: var(--color-text-muted, #8a8a94);
}
.rtgov-detail__note {
  margin: var(--space-2, 8px) 0 0;
  color: var(--color-text-muted, #8a8a94);
  font-size: var(--font-size-xs, 12px);
}
</style>
