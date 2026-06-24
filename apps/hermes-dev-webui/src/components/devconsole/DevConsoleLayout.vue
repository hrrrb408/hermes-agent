<script setup lang="ts">
import { computed, type Component } from 'vue'
import { ArrowLeft } from '@lucide/vue'
import { RouterLink } from 'vue-router'
import DevConsoleNav from './DevConsoleNav.vue'
import OverviewSection from './OverviewSection.vue'
import ToolExecutionSection from './ToolExecutionSection.vue'
import ProviderSection from './ProviderSection.vue'
import WriteRollbackSection from './WriteRollbackSection.vue'
import AuditViewerSection from './AuditViewerSection.vue'
import SafetySection from './SafetySection.vue'
import DiagnosticsSection from './DiagnosticsSection.vue'
import WorkflowSection from './WorkflowSection.vue'
import CapabilityRegistrySection from './CapabilityRegistrySection.vue'
import PluginDescriptorRegistrySection from './PluginDescriptorRegistrySection.vue'
import RuntimeGovernanceSection from './RuntimeGovernanceSection.vue'
import HumanReviewGovernanceSection from './HumanReviewGovernanceSection.vue'
import GovernanceHubSection from './GovernanceHubSection.vue'
import ThemeSwitcher from '@/components/theme/ThemeSwitcher.vue'
import { useDevConsoleNavStore, type DevConsoleSection } from '@/stores/devConsoleNav'

/**
 * Dev Console layout (Phase 2E): top bar + two-pane body (nav rail | content).
 *
 * The content area renders the active section via a dynamic component wrapped
 * in <KeepAlive> so each section's state (notably the AuditViewerPanel's shared
 * store data) survives section switches without being torn down.
 */
const nav = useDevConsoleNavStore()

const SECTIONS: Readonly<Record<DevConsoleSection, Component>> = {
  overview: OverviewSection,
  tools: ToolExecutionSection,
  provider: ProviderSection,
  write: WriteRollbackSection,
  audit: AuditViewerSection,
  safety: SafetySection,
  diagnostics: DiagnosticsSection,
  workflow: WorkflowSection,
  capabilities: CapabilityRegistrySection,
  plugins: PluginDescriptorRegistrySection,
  runtimeGovernance: RuntimeGovernanceSection,
  humanReview: HumanReviewGovernanceSection,
  governanceHub: GovernanceHubSection,
}

const activeComponent = computed<Component>(() => SECTIONS[nav.activeSection] ?? OverviewSection)
</script>

<template>
  <div class="devconsole">
    <header class="devconsole__topbar" role="banner">
      <div>
        <strong>Hermes Dev WebUI</strong>
        <span class="devconsole__badge">Dev Console</span>
      </div>
      <div class="devconsole__topbar-actions">
        <ThemeSwitcher />
        <RouterLink class="devconsole__back" to="/" aria-label="Back to Workspace">
          <ArrowLeft :size="15" aria-hidden="true" />
          Back to Workspace
        </RouterLink>
      </div>
    </header>

    <div class="devconsole__body">
      <DevConsoleNav />
      <main class="devconsole__content" role="main">
        <KeepAlive>
          <component :is="activeComponent" />
        </KeepAlive>
      </main>
    </div>
  </div>
</template>
