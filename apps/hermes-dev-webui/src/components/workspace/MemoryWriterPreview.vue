<script setup lang="ts">
/**
 * Memory Writer Preview panel — dry-run only.
 *
 * Provides WRITE, UPDATE, and ARCHIVE preview forms.
 * All operations are read-only dry-runs with zero side effects.
 * No execute/save/write-now buttons are ever shown.
 */
import { useMemoryWriterStore } from '@/stores/memoryWriter'
import type { MemoryWriterOperation } from '@/types/api/memory'

const store = useMemoryWriterStore()

const operations: { id: MemoryWriterOperation; label: string }[] = [
  { id: 'write', label: 'WRITE' },
  { id: 'update', label: 'UPDATE' },
  { id: 'archive', label: 'ARCHIVE' },
]

function runPreview(): void {
  switch (store.activeOperation) {
    case 'write':
      store.runWritePreview()
      break
    case 'update':
      store.runUpdatePreview()
      break
    case 'archive':
      store.runArchivePreview()
      break
  }
}

const IMPORTANCE_OPTIONS = ['P0', 'P1', 'P2', 'P3'] as const
const TTL_OPTIONS = ['permanent', 'project', 'session', 'temporary'] as const
</script>

<template>
  <section class="workspace-panel__section writer-preview" aria-label="Memory Writer Preview">
    <!-- Safety notice -->
    <div class="writer-safety-notice" role="status">
      Read-only preview · No files modified
    </div>

    <!-- Operation tabs -->
    <div class="writer-tabs" role="tablist" aria-label="Writer operation">
      <button
        v-for="op in operations"
        :key="op.id"
        role="tab"
        type="button"
        class="writer-tab"
        :class="{ 'writer-tab--active': store.activeOperation === op.id }"
        :aria-selected="store.activeOperation === op.id"
        :aria-controls="`writer-panel-${op.id}`"
        @click="store.setActiveOperation(op.id)"
      >
        {{ op.label }}
      </button>
    </div>

    <!-- WRITE form -->
    <div
      v-if="store.activeOperation === 'write'"
      id="writer-panel-write"
      role="tabpanel"
      class="writer-form"
    >
      <label class="writer-field">
        Query
        <textarea
          v-model="store.writeForm.query"
          class="writer-input writer-input--textarea"
          maxlength="2000"
          rows="2"
          placeholder="Enter the user message or context…"
        />
      </label>
      <label class="writer-field">
        Summary <span class="writer-required">*</span>
        <textarea
          v-model="store.writeForm.summary"
          class="writer-input writer-input--textarea"
          maxlength="1000"
          rows="2"
          placeholder="Memory summary…"
        />
      </label>
      <label class="writer-field">
        Title
        <input
          v-model="store.writeForm.title"
          class="writer-input"
          type="text"
          maxlength="120"
          placeholder="Optional title (derived from summary if omitted)"
        />
      </label>
      <label class="writer-field">
        Category <span class="writer-required">*</span>
        <input
          v-model="store.writeForm.category"
          class="writer-input"
          type="text"
          maxlength="100"
          placeholder="e.g. hermes"
        />
      </label>
      <div class="writer-row">
        <label class="writer-field writer-field--half">
          Importance
          <select v-model="store.writeForm.importance" class="writer-select">
            <option v-for="imp in IMPORTANCE_OPTIONS" :key="imp" :value="imp">{{ imp }}</option>
          </select>
        </label>
        <label class="writer-field writer-field--half">
          TTL
          <select v-model="store.writeForm.ttl" class="writer-select">
            <option v-for="ttl in TTL_OPTIONS" :key="ttl" :value="ttl">{{ ttl }}</option>
          </select>
        </label>
      </div>
      <label class="writer-field">
        Tags (comma-separated)
        <input
          v-model="store.writeForm.tags"
          class="writer-input"
          type="text"
          placeholder="hermes, test, memory-writer"
        />
      </label>
      <button
        type="button"
        class="writer-submit-btn"
        :disabled="store.isLoading || !store.writeForm.query || !store.writeForm.summary || !store.writeForm.category"
        @click="runPreview"
      >
        {{ store.isLoading ? 'Previewing…' : 'Preview WRITE' }}
      </button>
    </div>

    <!-- UPDATE form -->
    <div
      v-if="store.activeOperation === 'update'"
      id="writer-panel-update"
      role="tabpanel"
      class="writer-form"
    >
      <label class="writer-field">
        Memory ID <span class="writer-required">*</span>
        <input
          v-model="store.updateForm.memoryId"
          class="writer-input"
          type="text"
          placeholder="MEM-HERMES-001"
        />
      </label>
      <label class="writer-field">
        New Summary <span class="writer-required">*</span>
        <textarea
          v-model="store.updateForm.summary"
          class="writer-input writer-input--textarea"
          maxlength="1000"
          rows="2"
          placeholder="Updated summary…"
        />
      </label>
      <div class="writer-row">
        <label class="writer-field writer-field--half">
          Importance
          <select v-model="store.updateForm.importance" class="writer-select">
            <option value="">Unchanged</option>
            <option v-for="imp in IMPORTANCE_OPTIONS" :key="imp" :value="imp">{{ imp }}</option>
          </select>
        </label>
        <label class="writer-field writer-field--half">
          TTL
          <select v-model="store.updateForm.ttl" class="writer-select">
            <option value="">Unchanged</option>
            <option v-for="ttl in TTL_OPTIONS" :key="ttl" :value="ttl">{{ ttl }}</option>
          </select>
        </label>
      </div>
      <label class="writer-field">
        Tags (comma-separated)
        <input
          v-model="store.updateForm.tags"
          class="writer-input"
          type="text"
          placeholder="hermes, updated-tag"
        />
      </label>
      <button
        type="button"
        class="writer-submit-btn"
        :disabled="store.isLoading || !store.updateForm.memoryId || !store.updateForm.summary"
        @click="runPreview"
      >
        {{ store.isLoading ? 'Previewing…' : 'Preview UPDATE' }}
      </button>
    </div>

    <!-- ARCHIVE form -->
    <div
      v-if="store.activeOperation === 'archive'"
      id="writer-panel-archive"
      role="tabpanel"
      class="writer-form"
    >
      <label class="writer-field">
        Memory ID <span class="writer-required">*</span>
        <input
          v-model="store.archiveForm.memoryId"
          class="writer-input"
          type="text"
          placeholder="MEM-HERMES-001"
        />
      </label>
      <label class="writer-field">
        Reason (optional)
        <textarea
          v-model="store.archiveForm.reason"
          class="writer-input writer-input--textarea"
          maxlength="500"
          rows="2"
          placeholder="Why this memory should be archived…"
        />
      </label>
      <button
        type="button"
        class="writer-submit-btn"
        :disabled="store.isLoading || !store.archiveForm.memoryId"
        @click="runPreview"
      >
        {{ store.isLoading ? 'Previewing…' : 'Preview ARCHIVE' }}
      </button>
    </div>

    <!-- Loading -->
    <div v-if="store.isLoading" class="panel-loading" aria-busy="true" aria-live="polite">
      Running dry-run preview…
    </div>

    <!-- Error -->
    <div v-if="store.isError && store.previewError" class="panel-error" role="alert">
      <p>{{ store.previewError }}</p>
      <div class="panel-error__actions">
        <button type="button" class="panel-retry-btn" @click="runPreview">Retry</button>
        <button type="button" class="panel-retry-btn" @click="store.clearPreview">Clear</button>
      </div>
    </div>

    <!-- Result -->
    <div v-if="store.isSuccess && store.previewResult" class="writer-result" aria-live="polite">
      <div class="writer-result__header">
        <span class="writer-badge writer-badge--dry-run">Dry-run only</span>
        <span class="writer-badge" :class="store.previewResult.allowed ? 'writer-badge--allowed' : 'writer-badge--blocked'">
          {{ store.previewResult.allowed ? 'Allowed' : 'Blocked' }}
        </span>
        <span class="writer-badge writer-badge--decision">{{ store.previewResult.decision }}</span>
      </div>

      <div v-if="store.previewResult.blockedReason" class="writer-blocked-reason">
        {{ store.previewResult.blockedReason }}
      </div>

      <!-- No-effects confirmation -->
      <div v-if="store.previewResult.noEffects?.length" class="writer-no-effects">
        <div v-for="msg in store.previewResult.noEffects" :key="msg" class="writer-no-effect-item">
          ✓ {{ msg }}
        </div>
      </div>

      <!-- Safety -->
      <div class="writer-safety">
        <span>readOnly={{ store.previewResult.safety.readOnly }}</span>
        <span>sideEffects={{ store.previewResult.safety.sideEffects }}</span>
      </div>

      <!-- Score -->
      <details v-if="store.previewResult.score" class="writer-details">
        <summary>Score: {{ store.previewResult.score.total }}</summary>
        <dl class="context-list">
          <div v-for="entry in store.previewResult.score.breakdown" :key="entry.rule">
            <dt>{{ entry.rule }}</dt>
            <dd>{{ entry.value }}</dd>
          </div>
        </dl>
      </details>

      <!-- Similarity -->
      <details v-if="store.previewResult.similarity" class="writer-details">
        <summary>Similarity: {{ (store.previewResult.similarity.overall * 100).toFixed(1) }}%</summary>
        <dl class="context-list">
          <div><dt>Title</dt><dd>{{ (store.previewResult.similarity.title * 100).toFixed(1) }}%</dd></div>
          <div><dt>Summary</dt><dd>{{ (store.previewResult.similarity.summary * 100).toFixed(1) }}%</dd></div>
          <div><dt>Combined</dt><dd>{{ (store.previewResult.similarity.combined * 100).toFixed(1) }}%</dd></div>
          <div v-if="store.previewResult.similarity.matchedMemoryId">
            <dt>Matched</dt>
            <dd>{{ store.previewResult.similarity.matchedMemoryId }}</dd>
          </div>
        </dl>
      </details>

      <!-- Diff (UPDATE only) -->
      <details v-if="store.previewResult.diff" class="writer-details">
        <summary>Diff</summary>
        <dl class="context-list">
          <div><dt>Title changed</dt><dd>{{ store.previewResult.diff.titleChanged }}</dd></div>
          <div><dt>Summary changed</dt><dd>{{ store.previewResult.diff.summaryChanged }}</dd></div>
          <div><dt>Importance changed</dt><dd>{{ store.previewResult.diff.importanceChanged }}</dd></div>
          <div><dt>TTL changed</dt><dd>{{ store.previewResult.diff.ttlChanged }}</dd></div>
          <div v-if="store.previewResult.diff.tagsAdded.length"><dt>Tags added</dt><dd>{{ store.previewResult.diff.tagsAdded.join(', ') }}</dd></div>
          <div v-if="store.previewResult.diff.tagsRemoved.length"><dt>Tags removed</dt><dd>{{ store.previewResult.diff.tagsRemoved.join(', ') }}</dd></div>
        </dl>
      </details>

      <!-- Checks -->
      <details v-if="store.previewResult.checks.length" class="writer-details">
        <summary>Checks ({{ store.previewResult.checks.length }})</summary>
        <ul class="writer-check-list">
          <li v-for="check in store.previewResult.checks" :key="check.code" class="writer-check-item">
            <span :class="check.passed ? 'writer-check-pass' : 'writer-check-fail'">
              {{ check.passed ? '✓' : '✕' }}
            </span>
            {{ check.code }}: {{ check.message }}
          </li>
        </ul>
      </details>

      <!-- Effects -->
      <details v-if="store.previewResult.effects?.length" class="writer-details">
        <summary>Would-be effects ({{ store.previewResult.effects.length }})</summary>
        <ul class="writer-check-list">
          <li v-for="effect in store.previewResult.effects" :key="effect.type" class="writer-check-item">
            <span class="writer-check-info">◇</span>
            {{ effect.type }}{{ effect.wouldOccur ? '' : ' (skipped)' }}
          </li>
        </ul>
      </details>

      <!-- Warnings -->
      <div v-if="store.previewResult.warnings.length" class="writer-warnings">
        <div v-for="w in store.previewResult.warnings" :key="w" class="writer-warning-item">
          ⚠ {{ w }}
        </div>
      </div>

      <!-- Config thresholds -->
      <details class="writer-details">
        <summary>Config thresholds</summary>
        <dl class="context-list">
          <div><dt>Write threshold</dt><dd>{{ store.previewResult.config.writeThreshold }}</dd></div>
          <div><dt>Review threshold</dt><dd>{{ store.previewResult.config.reviewThreshold }}</dd></div>
          <div><dt>Update similarity</dt><dd>{{ store.previewResult.config.updateSimilarityThreshold }}</dd></div>
          <div><dt>Duplicate similarity</dt><dd>{{ store.previewResult.config.duplicateSimilarityThreshold }}</dd></div>
        </dl>
      </details>
    </div>
  </section>
</template>
