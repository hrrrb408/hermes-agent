<script setup lang="ts">
import AppLayout from '@/components/layout/AppLayout.vue'
import { useUiStore } from '@/stores/ui'

useUiStore().initializeUiState()
</script>

<template>
  <AppLayout />
</template>
