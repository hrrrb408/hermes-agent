<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useMemoryStore } from '@/stores/workspacePanel'
import type { MemoryItem } from '@/types/api/memory'

const store = useMemoryStore()

onMounted(async () => {
  await store.loadStatus()
  if (store.isAvailable) {
    await Promise.all([store.loadCategories(), store.loadItems()])
  }
})

watch(() => store.includeArchived, async () => {
  await Promise.all([store.loadCategories(), store.loadItems()])
})

async function retryAll(): Promise<void> {
  await store.loadStatus()
  if (store.isAvailable) {
    await Promise.all([store.loadCategories(), store.loadItems()])
  }
}

async function selectItem(item: MemoryItem): Promise<void> {
  if (store.detail?.id === item.id) {
    store.clearDetail()
  } else {
    await store.loadDetail(item.id)
  }
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Memory">
    <!-- Status badge -->
    <div class="panel-header">
      <span class="panel-badge" :class="{ 'panel-badge--active': store.isAvailable }">
        {{ store.isAvailable ? 'Read-only' : 'Unavailable' }}
      </span>
      <span v-if="store.status" class="panel-count">
        {{ store.status.memories.active }} memories
      </span>
    </div>

    <!-- Error state -->
    <div v-if="store.statusState === 'error'" class="panel-error" role="alert">
      <p>{{ store.statusError }}</p>
      <button type="button" class="panel-retry-btn" aria-label="Retry loading memory status" @click="retryAll">Retry</button>
    </div>

    <!-- Loading state -->
    <div v-else-if="store.statusState === 'loading'" class="panel-loading" aria-busy="true" aria-live="polite">
      Loading memory data…
    </div>

    <!-- Unavailable state -->
    <div v-else-if="store.statusState === 'empty' && !store.isAvailable" class="panel-empty">
      Memory system is not available.
    </div>

    <!-- Available content -->
    <template v-else-if="store.isAvailable">
      <!-- Archived toggle -->
      <label class="panel-toggle">
        <input
          type="checkbox"
          :checked="store.includeArchived"
          @change="store.setIncludeArchived(($event.target as HTMLInputElement).checked)"
        />
        Include archived
      </label>

      <!-- Detail view -->
      <article v-if="store.detail" class="panel-card panel-card--detail">
        <div class="panel-card__header">
          <strong>{{ store.detail.id }}</strong>
          <button
            type="button"
            class="panel-card__close"
            aria-label="Close detail"
            @click="store.clearDetail()"
          >
            ✕
          </button>
        </div>
        <h4>{{ store.detail.title }}</h4>
        <dl class="context-list">
          <div><dt>Category</dt><dd>{{ store.detail.category }}</dd></div>
          <div><dt>Type</dt><dd>{{ store.detail.type }}</dd></div>
          <div><dt>Importance</dt><dd>{{ store.detail.importance }}</dd></div>
          <div><dt>Status</dt><dd>{{ store.detail.status }}</dd></div>
          <div><dt>Tags</dt><dd>{{ store.detail.tags }}</dd></div>
          <div><dt>Updated</dt><dd>{{ store.detail.updatedAt }}</dd></div>
        </dl>
        <p v-if="store.detail.summary" class="panel-card__summary">
          {{ store.detail.summary }}
        </p>
        <details v-if="store.detail.recordPreview" class="panel-card__details">
          <summary>Record preview</summary>
          <pre class="panel-card__pre">{{ store.detail.recordPreview }}</pre>
          <span v-if="store.detail.truncated" class="panel-truncated">Truncated</span>
        </details>
      </article>

      <!-- Item list -->
      <template v-else>
        <!-- Category chips -->
        <div v-if="store.categories.length > 0" class="panel-chips">
          <button
            type="button"
            class="panel-chip"
            :class="{ 'panel-chip--active': !store.categoryFilter }"
            @click="store.setCategoryFilter(''); store.loadItems()"
          >
            All
          </button>
          <button
            v-for="cat in store.activeCategories"
            :key="cat.key"
            type="button"
            class="panel-chip"
            :class="{ 'panel-chip--active': store.categoryFilter === cat.key }"
            @click="store.setCategoryFilter(cat.key); store.loadItems()"
          >
            {{ cat.title }} ({{ cat.activeMemoryCount }})
          </button>
        </div>

        <!-- Items error -->
        <div v-if="store.itemsState === 'error'" class="panel-error" role="alert">
          <p>{{ store.itemsError }}</p>
          <button type="button" class="panel-retry-btn" aria-label="Retry loading memory items" @click="store.loadItems()">Retry</button>
        </div>

        <!-- Items loading -->
        <div v-else-if="store.itemsState === 'loading'" class="panel-loading" aria-busy="true">
          Loading items…
        </div>

        <!-- Items empty -->
        <div v-else-if="store.itemsState === 'empty'" class="panel-empty">
          No memory items found.
        </div>

        <!-- Items list -->
        <div v-else-if="store.itemsState === 'success'" class="panel-items">
          <article
            v-for="item in store.items"
            :key="item.id"
            class="panel-card panel-card--clickable"
            role="button"
            tabindex="0"
            :aria-label="`View ${item.id}`"
            @click="selectItem(item)"
            @keydown.enter="selectItem(item)"
            @keydown.space.prevent="selectItem(item)"
          >
            <div class="panel-card__header">
              <strong>{{ item.id }}</strong>
              <span class="panel-card__importance">{{ item.importance }}</span>
            </div>
            <h4>{{ item.title }}</h4>
            <p v-if="item.summary" class="panel-card__summary">{{ item.summary }}</p>
            <div class="panel-card__meta">
              <span>{{ item.category }}</span>
              <span>{{ item.status }}</span>
            </div>
          </article>
        </div>
      </template>
    </template>
  </section>
</template>
