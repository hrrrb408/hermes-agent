<script setup lang="ts">
import { onMounted } from 'vue'
import { useContextStore } from '@/stores/workspacePanel'

const store = useContextStore()

onMounted(() => {
  // Context panel starts idle — user must trigger preview manually
})

async function runPreview(): Promise<void> {
  if (!store.query.trim()) return
  await store.runPreview()
}
</script>

<template>
  <section class="workspace-panel__section" aria-label="Context Preview">
    <!-- Header badges -->
    <div class="panel-header">
      <span class="panel-badge">No LLM</span>
      <span class="panel-badge">No writes</span>
    </div>

    <!-- Query input -->
    <form class="panel-form" @submit.prevent="runPreview">
      <label class="panel-form__label" for="context-query-input">
        Query
      </label>
      <input
        id="context-query-input"
        v-model="store.query"
        type="text"
        class="panel-form__input"
        placeholder="Enter a query to preview memory context…"
        maxlength="1000"
        autocomplete="off"
      />
      <button
        type="submit"
        class="panel-form__submit"
        :disabled="store.state === 'loading' || !store.query.trim()"
      >
        {{ store.state === 'loading' ? 'Loading…' : 'Preview' }}
      </button>
    </form>

    <!-- Error state -->
    <div v-if="store.state === 'error'" class="panel-error">
      <p>{{ store.error }}</p>
      <button type="button" class="panel-retry-btn" @click="runPreview">Retry</button>
    </div>

    <!-- Results -->
    <template v-if="store.preview && store.state !== 'loading'">
      <!-- Side effects guarantee -->
      <div class="panel-guarantee">
        Side effects: {{ store.preview.sideEffects ? 'Yes' : 'None' }}
      </div>

      <!-- Matched categories -->
      <div v-if="store.preview.matchedCategories.length > 0" class="panel-section">
        <h4>Matched Categories</h4>
        <div class="panel-items">
          <article
            v-for="cat in store.preview.matchedCategories"
            :key="cat.key"
            class="panel-card"
          >
            <div class="panel-card__header">
              <strong>{{ cat.title }}</strong>
              <span class="panel-card__score">Score: {{ cat.score }}</span>
            </div>
            <div class="panel-card__meta">
              <span>Priority: {{ cat.priority }}</span>
            </div>
          </article>
        </div>
      </div>

      <!-- Matched memories -->
      <div v-if="store.preview.memories.length > 0" class="panel-section">
        <h4>Loaded Memories</h4>
        <div class="panel-items">
          <article
            v-for="mem in store.preview.memories"
            :key="mem.id"
            class="panel-card"
          >
            <div class="panel-card__header">
              <strong>{{ mem.id }}</strong>
              <span class="panel-card__score">Score: {{ mem.score }}</span>
            </div>
            <h5>{{ mem.title }}</h5>
            <p v-if="mem.summary" class="panel-card__summary">{{ mem.summary }}</p>
            <div class="panel-card__meta">
              <span>{{ mem.category }}</span>
              <span v-if="mem.truncated" class="panel-truncated">Truncated</span>
            </div>
          </article>
        </div>
      </div>

      <!-- Empty results -->
      <div v-if="store.preview.memories.length === 0 && store.state === 'empty'" class="panel-empty">
        No matching memories found for this query.
      </div>

      <!-- Limits info -->
      <div class="panel-limits">
        Limits: {{ store.preview.limits.maxCategories }} categories,
        {{ store.preview.limits.maxMemories }} memories,
        {{ store.preview.limits.maxRecordChars }} chars
      </div>
    </template>

    <!-- Empty initial state -->
    <div v-if="store.state === 'idle'" class="panel-empty">
      Enter a query and click Preview to see matching memory context.
    </div>
  </section>
</template>
