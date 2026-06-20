<script setup lang="ts">
import {
  Activity,
  ClipboardList,
  FilePen,
  LayoutDashboard,
  ListChecks,
  Plug,
  Puzzle,
  ScrollText,
  ShieldCheck,
  Workflow,
  Wrench,
} from '@lucide/vue'
import { useDevConsoleNavStore, CONSOLE_SECTIONS, CONSOLE_SECTION_LABELS, type DevConsoleSection } from '@/stores/devConsoleNav'
import type { Component } from 'vue'

/**
 * Dev Console left nav rail (Phase 2E).
 *
 * Roving-tabindex keyboard navigation (ArrowUp/Down/Home/End), mirroring the
 * WorkspacePanel tab pattern. Active section persists via the devConsoleNav
 * store.
 */
const nav = useDevConsoleNavStore()

const ICONS: Readonly<Record<DevConsoleSection, Component>> = {
  overview: LayoutDashboard,
  tools: Wrench,
  provider: Plug,
  write: FilePen,
  audit: ClipboardList,
  safety: ShieldCheck,
  diagnostics: Activity,
  workflow: Workflow,
  capabilities: ListChecks,
  plugins: Puzzle,
  runtimeGovernance: ScrollText,
}

function select(section: DevConsoleSection): void {
  nav.setSection(section)
}

function onKeyDown(event: KeyboardEvent, section: DevConsoleSection): void {
  if (!['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()

  const currentIndex = CONSOLE_SECTIONS.indexOf(section)
  let nextIndex = currentIndex
  if (event.key === 'Home') nextIndex = 0
  if (event.key === 'End') nextIndex = CONSOLE_SECTIONS.length - 1
  if (event.key === 'ArrowUp' || event.key === 'ArrowLeft') {
    nextIndex = (currentIndex - 1 + CONSOLE_SECTIONS.length) % CONSOLE_SECTIONS.length
  }
  if (event.key === 'ArrowDown' || event.key === 'ArrowRight') {
    nextIndex = (currentIndex + 1) % CONSOLE_SECTIONS.length
  }

  const next = CONSOLE_SECTIONS[nextIndex]
  if (!next) return
  select(next)
  document.getElementById(`devconsole-nav-${next}`)?.focus()
}
</script>

<template>
  <nav class="devconsole-nav" aria-label="Developer console sections">
    <div class="devconsole-nav__heading">Console</div>
    <div role="tablist" aria-orientation="vertical" aria-label="Developer console navigation">
      <button
        v-for="section in CONSOLE_SECTIONS"
        :id="`devconsole-nav-${section}`"
        :key="section"
        type="button"
        role="tab"
        class="devconsole-nav__item"
        :class="{ 'devconsole-nav__item--active': nav.activeSection === section }"
        :aria-selected="nav.activeSection === section"
        :tabindex="nav.activeSection === section ? 0 : -1"
        @click="select(section)"
        @keydown="onKeyDown($event, section)"
      >
        <component :is="ICONS[section]" :size="15" aria-hidden="true" />
        <span>{{ CONSOLE_SECTION_LABELS[section] }}</span>
      </button>
    </div>
  </nav>
</template>
