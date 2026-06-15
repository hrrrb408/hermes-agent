<script setup lang="ts">
import DevConsoleLayout from '@/components/devconsole/DevConsoleLayout.vue'
import { useDevConsoleNavStore } from '@/stores/devConsoleNav'

// Restore the persisted active section on entry.
useDevConsoleNavStore().initializeNavState()
</script>

<template>
  <DevConsoleLayout />
</template>
