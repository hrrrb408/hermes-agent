<script setup lang="ts">
import { ref } from 'vue'
import { onMounted, watch } from 'vue'
import { useReviewStore } from '@/stores/review'

const store = useReviewStore()

// Confirmation dialog state
const confirmText = ref('')
const ackWriteMemory = ref(false)
const ackUpdateReview = ref(false)
const ackAppendEvent = ref(false)
const ackRejectUpdateReview = ref(false)
const ackRejectAppendEvent = ref(false)

onMounted(async () => {
  await store.loadStatus()
  if (store.isAvailable) {
    await store.loadReviews()
  }
})

// Reload list when filters change
watch([
  () => store.statusFilter,
  () => store.decisionFilter,
  () => store.categoryFilter,
  () => store.queryFilter,
  () => store.orderFilter,
], async () => {
  if (store.isAvailable) {
    await store.loadReviews()
  }
})

async function retryAll(): Promise<void> {
  await store.loadStatus()
  if (store.isAvailable) {
    await store.loadReviews()
  }
}

function handleSearchKeydown(event: KeyboardEvent): void {
  if (event.key === 'Enter') {
    store.loadReviews()
  }
}

function handleApproveDryRun(): void {
  if (!store.detail || store.detail.status !== 'pending') return
  store.runApproveDryRun(store.detail.reviewId)
}

function handleRejectDryRun(): void {
  if (!store.detail || store.detail.status !== 'pending') return
  store.runRejectDryRun(store.detail.reviewId)
}

function handleCloseDryRun(): void {
  store.clearDryRun()
}

// ── Execute handlers ──

function handleApproveExecute(): void {
  if (!store.detail || store.detail.status !== 'pending') return
  if (!store.isExecuteEnabled) return
  if (!store.dryRunResult || store.dryRunAction !== 'APPROVE') return
  resetConfirmState()
  store.openConfirmDialog('APPROVE')
}

function handleRejectExecute(): void {
  if (!store.detail || store.detail.status !== 'pending') return
  if (!store.isExecuteEnabled) return
  if (!store.dryRunResult || store.dryRunAction !== 'REJECT') return
  resetConfirmState()
  store.openConfirmDialog('REJECT')
}

function resetConfirmState(): void {
  confirmText.value = ''
  ackWriteMemory.value = false
  ackUpdateReview.value = false
  ackAppendEvent.value = false
  ackRejectUpdateReview.value = false
  ackRejectAppendEvent.value = false
}

function handleCancelConfirm(): void {
  store.closeConfirmDialog()
}

function handleSubmitConfirm(): void {
  if (!store.detail) return
  if (!store.dryRunResult) return

  const updatedAt = store.detail.updatedAt

  if (store.executeAction === 'APPROVE') {
    if (confirmText.value !== 'APPROVE') return
    if (!ackWriteMemory.value || !ackUpdateReview.value || !ackAppendEvent.value) return
    store.executeApprove(store.detail.reviewId, {
      confirmationText: 'APPROVE',
      expectedAction: 'APPROVE',
      reviewUpdatedAt: updatedAt,
      dryRunPreviewed: true,
      acknowledgedEffects: ['WRITE_MEMORY', 'UPDATE_REVIEW', 'APPEND_REVIEW_EVENT'],
    })
  } else if (store.executeAction === 'REJECT') {
    if (confirmText.value !== 'REJECT') return
    if (!ackRejectUpdateReview.value || !ackRejectAppendEvent.value) return
    store.executeReject(store.detail.reviewId, {
      confirmationText: 'REJECT',
      expectedAction: 'REJECT',
      reviewUpdatedAt: updatedAt,
      dryRunPreviewed: true,
      acknowledgedEffects: ['UPDATE_REVIEW', 'APPEND_REVIEW_EVENT'],
    })
  }
}

const canSubmitConfirm = (() => {
  if (store.executeAction === 'APPROVE') {
    return confirmText.value === 'APPROVE' && ackWriteMemory.value && ackUpdateReview.value && ackAppendEvent.value
  }
  if (store.executeAction === 'REJECT') {
    return confirmText.value === 'REJECT' && ackRejectUpdateReview.value && ackRejectAppendEvent.value
  }
  return false
})()
</script>

<template>
  <section class="workspace-panel__section" aria-label="Review Queue">
    <!-- Status header -->
    <div class="panel-header">
      <span class="panel-badge" :class="{ 'panel-badge--active': store.isAvailable }">
        {{ store.isAvailable ? 'Read-only' : 'Unavailable' }}
      </span>
      <span v-if="store.isAvailable" class="panel-count">
        {{ store.totalCount }} items
      </span>
      <span class="panel-phase-badge" title="Dev-only execute in Phase 1C">1C</span>
    </div>

    <!-- Error state -->
    <div v-if="store.statusState === 'error'" class="panel-error" role="alert">
      <p>{{ store.statusError }}</p>
      <button type="button" class="panel-retry-btn" aria-label="Retry loading review status" @click="retryAll">Retry</button>
    </div>

    <!-- Loading state -->
    <div v-else-if="store.statusState === 'loading'" class="panel-loading" aria-busy="true" aria-live="polite">
      Loading review queue…
    </div>

    <!-- Unavailable state -->
    <div v-else-if="store.statusState === 'empty' && !store.isAvailable" class="panel-empty">
      Review queue is not available.
    </div>

    <!-- Available content -->
    <template v-else-if="store.isAvailable">
      <!-- Counts summary -->
      <div class="review-counts">
        <span class="review-count" title="Pending reviews">
          <span class="review-count__dot review-count__dot--pending"></span>
          {{ store.status?.counts.pending ?? 0 }} pending
        </span>
        <span class="review-count" title="Approved reviews">
          <span class="review-count__dot review-count__dot--approved"></span>
          {{ store.status?.counts.approved ?? 0 }}
        </span>
        <span class="review-count" title="Rejected reviews">
          <span class="review-count__dot review-count__dot--rejected"></span>
          {{ store.status?.counts.rejected ?? 0 }}
        </span>
        <span v-if="(store.status?.counts.failed ?? 0) > 0" class="review-count" title="Failed reviews">
          <span class="review-count__dot review-count__dot--failed"></span>
          {{ store.status?.counts.failed }}
        </span>
      </div>

      <!-- Filters -->
      <div class="review-filters">
        <select
          class="review-filter-select"
          :value="store.statusFilter ?? ''"
          aria-label="Filter by status"
          @change="store.setStatusFilter(($event.target as HTMLSelectElement).value as any || undefined)"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="failed">Failed</option>
        </select>

        <select
          class="review-filter-select"
          :value="store.decisionFilter ?? ''"
          aria-label="Filter by decision"
          @change="store.setDecisionFilter(($event.target as HTMLSelectElement).value as any || undefined)"
        >
          <option value="">All decisions</option>
          <option value="WRITE">WRITE</option>
          <option value="UPDATE">UPDATE</option>
          <option value="REVIEW">REVIEW</option>
          <option value="UNDECIDED">UNDECIDED</option>
        </select>

        <input
          type="search"
          class="review-search"
          placeholder="Search reviews…"
          :value="store.queryFilter"
          aria-label="Search reviews"
          @input="store.setQueryFilter(($event.target as HTMLInputElement).value)"
          @keydown="handleSearchKeydown"
        />

        <button
          type="button"
          class="panel-retry-btn review-refresh-btn"
          aria-label="Refresh reviews"
          title="Refresh"
          @click="store.refresh()"
        >
          ↻
        </button>
      </div>

      <!-- Detail view -->
      <article v-if="store.detail" class="panel-card panel-card--detail">
        <div class="panel-card__header">
          <strong>{{ store.detail.reviewId }}</strong>
          <button
            type="button"
            class="panel-card__close"
            aria-label="Close detail"
            @click="store.clearSelection()"
          >
            ✕
          </button>
        </div>

        <div class="review-detail-badges">
          <span class="review-status-badge" :class="`review-status-badge--${store.detail.status}`">
            {{ store.detail.status }}
          </span>
          <span class="review-action-badge">{{ store.detail.proposedAction }}</span>
          <span v-if="store.detail.protectedTarget" class="review-protected-badge" title="Target is protected">🛡</span>
        </div>

        <h4>{{ store.detail.title }}</h4>

        <p v-if="store.detail.summary" class="panel-card__summary">
          {{ store.detail.summary }}
        </p>

        <dl class="context-list">
          <div><dt>Category</dt><dd>{{ store.detail.category }}</dd></div>
          <div><dt>Decision</dt><dd>{{ store.detail.decision }}</dd></div>
          <div><dt>Score</dt><dd>{{ store.detail.score }}</dd></div>
          <div><dt>Occurrences</dt><dd>{{ store.detail.occurrenceCount }}</dd></div>
          <div v-if="store.detail.targetMemoryId"><dt>Target</dt><dd>{{ store.detail.targetMemoryId }}</dd></div>
          <div><dt>Tags</dt><dd>{{ store.detail.tags.join(', ') }}</dd></div>
        </dl>

        <!-- Score breakdown -->
        <details v-if="store.detail.scoreBreakdown.length > 0" class="panel-card__details">
          <summary>Score breakdown</summary>
          <ul class="review-breakdown-list">
            <li v-for="entry in store.detail.scoreBreakdown" :key="entry.rule">
              {{ entry.rule }}: {{ entry.value }}
            </li>
          </ul>
        </details>

        <!-- Similarity -->
        <details class="panel-card__details">
          <summary>Similarity</summary>
          <dl class="context-list">
            <div><dt>Title</dt><dd>{{ (store.detail.similarity.title * 100).toFixed(1) }}%</dd></div>
            <div><dt>Summary</dt><dd>{{ (store.detail.similarity.summary * 100).toFixed(1) }}%</dd></div>
            <div><dt>Combined</dt><dd>{{ (store.detail.similarity.combined * 100).toFixed(1) }}%</dd></div>
            <div><dt>Overall</dt><dd>{{ (store.detail.similarity.overall * 100).toFixed(1) }}%</dd></div>
          </dl>
        </details>

        <!-- Reason codes -->
        <div v-if="store.detail.reasonCodes.length > 0" class="review-reason-codes">
          <span v-for="code in store.detail.reasonCodes" :key="code" class="review-reason-code">
            {{ code }}
          </span>
        </div>

        <!-- Error info -->
        <div v-if="store.detail.errors.lastError" class="panel-error" role="alert">
          <p>{{ store.detail.errors.lastError }}</p>
        </div>

        <!-- Timestamps -->
        <div class="review-timestamps">
          <span :title="'Created: ' + store.detail.timestamps.createdAt">Created {{ store.detail.timestamps.createdAt.slice(0, 10) }}</span>
          <span :title="'Updated: ' + store.detail.timestamps.updatedAt">Updated {{ store.detail.timestamps.updatedAt.slice(0, 10) }}</span>
        </div>

        <!-- Dry-run controls (only for pending items) -->
        <div v-if="store.detail.status === 'pending'" class="review-dry-run-controls">
          <button
            type="button"
            class="dry-run-btn dry-run-btn--approve"
            :disabled="store.isDryRunLoading"
            aria-label="Preview approve action (dry-run)"
            @click="handleApproveDryRun"
          >
            Approve dry-run
          </button>
          <button
            type="button"
            class="dry-run-btn dry-run-btn--reject"
            :disabled="store.isDryRunLoading"
            aria-label="Preview reject action (dry-run)"
            @click="handleRejectDryRun"
          >
            Reject dry-run
          </button>
        </div>
        <div v-else class="review-dry-run-controls">
          <span class="dry-run-disabled-notice">
            Dry-run only available for pending items (current: {{ store.detail.status }}).
          </span>
        </div>

        <!-- Dry-run result panel -->
        <div v-if="store.dryRunResult" class="dry-run-result" role="region" aria-label="Dry-run result">
          <div class="dry-run-result__header">
            <strong>{{ store.dryRunResult.action }} dry-run</strong>
            <span
              class="dry-run-result__status"
              :class="store.dryRunResult.allowed ? 'dry-run-result__status--allowed' : 'dry-run-result__status--blocked'"
            >
              {{ store.dryRunResult.allowed ? 'Would succeed' : 'Blocked' }}
            </span>
            <button
              type="button"
              class="panel-card__close"
              aria-label="Close dry-run result"
              @click="handleCloseDryRun"
            >
              ✕
            </button>
          </div>

          <div v-if="store.dryRunResult.blockedReason" class="dry-run-result__blocked-reason" role="alert">
            {{ store.dryRunResult.blockedReason }}
          </div>

          <!-- Would-do flags -->
          <dl class="context-list dry-run-result__flags">
            <div>
              <dt>Would modify</dt>
              <dd>{{ store.dryRunResult.wouldModify ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Would write memory</dt>
              <dd>{{ store.dryRunResult.wouldWriteMemory ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Would update review</dt>
              <dd>{{ store.dryRunResult.wouldUpdateReview ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Would append event</dt>
              <dd>{{ store.dryRunResult.wouldAppendEvent ? 'Yes' : 'No' }}</dd>
            </div>
          </dl>

          <!-- Target info -->
          <div v-if="store.dryRunResult.target" class="dry-run-result__target">
            <dl class="context-list">
              <div v-if="store.dryRunResult.target.memoryId">
                <dt>Target memory</dt>
                <dd>{{ store.dryRunResult.target.memoryId }}</dd>
              </div>
              <div>
                <dt>Category</dt>
                <dd>{{ store.dryRunResult.target.category }}</dd>
              </div>
              <div>
                <dt>Operation</dt>
                <dd>{{ store.dryRunResult.target.operation }}</dd>
              </div>
            </dl>
          </div>

          <!-- Validation checks -->
          <details v-if="store.dryRunResult.checks.length > 0" class="panel-card__details" open>
            <summary>Checks ({{ store.dryRunResult.checks.length }})</summary>
            <ul class="dry-run-check-list">
              <li
                v-for="check in store.dryRunResult.checks"
                :key="check.code"
                class="dry-run-check-item"
                :class="`dry-run-check-item--${check.status}`"
              >
                <span class="dry-run-check-item__icon">{{ check.status === 'pass' ? '✓' : '✗' }}</span>
                <span class="dry-run-check-item__code">{{ check.code }}</span>
                <span class="dry-run-check-item__message">{{ check.message }}</span>
              </li>
            </ul>
          </details>

          <!-- Safety -->
          <div class="dry-run-result__safety">
            <span class="review-safety__badge">🔒 Dev-only · Production blocked</span>
          </div>

          <!-- Effects / No effects -->
          <div v-if="store.dryRunResult.effects.length > 0" class="dry-run-result__effects">
            <p class="dry-run-result__label">Would do:</p>
            <ul>
              <li v-for="(effect, idx) in store.dryRunResult.effects" :key="idx">{{ effect }}</li>
            </ul>
          </div>

          <div class="dry-run-result__no-effects">
            <p class="dry-run-result__label">Safety:</p>
            <ul>
              <li v-for="(item, idx) in store.dryRunResult.noEffects" :key="idx">{{ item }}</li>
            </ul>
          </div>

          <!-- Warnings -->
          <div v-if="store.dryRunResult.warnings.length > 0" class="dry-run-result__warnings" role="alert">
            <p class="dry-run-result__label">Warnings:</p>
            <ul>
              <li v-for="(warning, idx) in store.dryRunResult.warnings" :key="idx">{{ warning }}</li>
            </ul>
          </div>
        </div>

        <!-- Dry-run loading -->
        <div v-if="store.isDryRunLoading" class="panel-loading" aria-busy="true">
          Running dry-run preview…
        </div>

        <!-- Dry-run error -->
        <div v-if="store.dryRunError" class="panel-error" role="alert">
          <p>{{ store.dryRunError }}</p>
          <button type="button" class="panel-retry-btn" @click="handleApproveDryRun">Retry</button>
        </div>

        <!-- Safety area -->
        <div class="review-safety">
          <span class="review-safety__badge" title="Dev-only execute with kill switch">
            🔒 Dev-only ·
            <template v-if="store.isKillSwitchActive">Execute disabled (kill switch active)</template>
            <template v-else-if="store.isExecuteEnabled">Execute enabled</template>
            <template v-else>Dry-run preview</template>
          </span>
        </div>

        <!-- Execute capability area (Phase 1C) -->
        <div v-if="store.detail.status === 'pending'" class="review-execute-area">
          <h5>Execute controls</h5>

          <div class="review-execute-status">
            <span v-if="store.isKillSwitchActive" class="review-execute-notice">
              ⚠️ Execute is disabled by default. Enable with HERMES_REVIEW_EXECUTE_ENABLED=true.
            </span>
            <span v-else-if="store.isExecuteEnabled" class="review-execute-notice review-execute-notice--enabled">
              ✅ Execute enabled (dev-only). This will modify dev memory files.
            </span>
            <span v-else class="review-execute-notice">
              Dry-run first, then execute if kill switch is enabled.
            </span>
          </div>

          <!-- Execute buttons -->
          <div class="review-execute-buttons">
            <button
              type="button"
              class="dry-run-btn dry-run-btn--approve"
              :disabled="!store.isExecuteEnabled || !store.dryRunResult || store.dryRunAction !== 'APPROVE' || store.isExecuteLoading || store.isDryRunLoading"
              aria-label="Execute approve action (dev-only)"
              title="Requires dry-run first and kill switch enabled"
              @click="handleApproveExecute"
            >
              Approve execute
            </button>
            <button
              type="button"
              class="dry-run-btn dry-run-btn--reject"
              :disabled="!store.isExecuteEnabled || !store.dryRunResult || store.dryRunAction !== 'REJECT' || store.isExecuteLoading || store.isDryRunLoading"
              aria-label="Execute reject action (dev-only)"
              title="Requires dry-run first and kill switch enabled"
              @click="handleRejectExecute"
            >
              Reject execute
            </button>
          </div>

          <p v-if="store.isExecuteEnabled" class="review-execute-warning">
            ⚠️ These buttons will modify dev memory files. This cannot be undone.
          </p>
        </div>

        <!-- Execute result panel -->
        <div v-if="store.executeResult" class="dry-run-result" role="region" aria-label="Execute result">
          <div class="dry-run-result__header">
            <strong>{{ store.executeResult.action }} execute</strong>
            <span class="dry-run-result__status dry-run-result__status--allowed">
              Executed
            </span>
          </div>
          <dl class="context-list">
            <div>
              <dt>Status</dt>
              <dd>{{ store.executeResult.statusBefore }} → {{ store.executeResult.statusAfter }}</dd>
            </div>
            <div>
              <dt>Memory changed</dt>
              <dd>{{ store.executeResult.memoryChanged ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Review changed</dt>
              <dd>{{ store.executeResult.reviewChanged ? 'Yes' : 'No' }}</dd>
            </div>
            <div>
              <dt>Event appended</dt>
              <dd>{{ store.executeResult.eventAppended ? 'Yes' : 'No' }}</dd>
            </div>
            <div v-if="store.executeResult.target.memoryId">
              <dt>Target</dt>
              <dd>{{ store.executeResult.target.memoryId }}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{{ store.executeResult.target.category }}</dd>
            </div>
            <div>
              <dt>Operation</dt>
              <dd>{{ store.executeResult.target.operation }}</dd>
            </div>
          </dl>
          <div class="dry-run-result__safety">
            <span class="review-safety__badge">🔒 Dev-only · {{ store.executeResult.audit.timestamp }}</span>
          </div>
        </div>

        <!-- Execute loading -->
        <div v-if="store.isExecuteLoading" class="panel-loading" aria-busy="true">
          Executing…
        </div>

        <!-- Execute error -->
        <div v-if="store.executeError" class="panel-error" role="alert">
          <p>{{ store.executeError }}</p>
          <button type="button" class="panel-retry-btn" @click="store.clearExecute()">Dismiss</button>
        </div>

        <!-- Confirmation dialog -->
        <div v-if="store.showConfirmDialog" class="review-confirm-dialog" role="dialog" aria-label="Confirm execute">
          <h5>⚠️ Confirm {{ store.executeAction }} execute</h5>
          <p>This will modify dev memory files. This cannot be undone.</p>

          <label class="review-confirm-label">
            Type {{ store.executeAction }} to confirm:
            <input
              v-model="confirmText"
              type="text"
              class="review-confirm-input"
              :placeholder="store.executeAction ?? ''"
              autocomplete="off"
            />
          </label>

          <template v-if="store.executeAction === 'APPROVE'">
            <p class="review-confirm-effects-label">Acknowledged effects:</p>
            <label class="review-confirm-checkbox">
              <input v-model="ackWriteMemory" type="checkbox" />
              WRITE_MEMORY — Creates memory record
            </label>
            <label class="review-confirm-checkbox">
              <input v-model="ackUpdateReview" type="checkbox" />
              UPDATE_REVIEW — Changes review status
            </label>
            <label class="review-confirm-checkbox">
              <input v-model="ackAppendEvent" type="checkbox" />
              APPEND_REVIEW_EVENT — Logs audit event
            </label>
          </template>

          <template v-else>
            <p class="review-confirm-effects-label">Acknowledged effects:</p>
            <label class="review-confirm-checkbox">
              <input v-model="ackRejectUpdateReview" type="checkbox" />
              UPDATE_REVIEW — Changes review status
            </label>
            <label class="review-confirm-checkbox">
              <input v-model="ackRejectAppendEvent" type="checkbox" />
              APPEND_REVIEW_EVENT — Logs audit event
            </label>
          </template>

          <div class="review-confirm-actions">
            <button type="button" class="panel-retry-btn" @click="handleCancelConfirm">Cancel</button>
            <button
              type="button"
              class="dry-run-btn"
              :class="store.executeAction === 'APPROVE' ? 'dry-run-btn--approve' : 'dry-run-btn--reject'"
              :disabled="!canSubmitConfirm || store.isExecuteLoading"
              @click="handleSubmitConfirm"
            >
              Execute {{ store.executeAction }}
            </button>
          </div>
        </div>
      </article>

      <!-- List view -->
      <template v-else>
        <!-- List error -->
        <div v-if="store.listState === 'error'" class="panel-error" role="alert">
          <p>{{ store.listError }}</p>
          <button type="button" class="panel-retry-btn" aria-label="Retry loading reviews" @click="store.loadReviews()">Retry</button>
        </div>

        <!-- List loading -->
        <div v-else-if="store.listState === 'loading'" class="panel-loading" aria-busy="true">
          Loading reviews…
        </div>

        <!-- List empty -->
        <div v-else-if="store.listState === 'empty'" class="panel-empty">
          No review items found.
        </div>

        <!-- Items list -->
        <div v-else-if="store.listState === 'success'" class="panel-items">
          <article
            v-for="item in store.items"
            :key="item.reviewId"
            class="panel-card panel-card--clickable"
            role="button"
            tabindex="0"
            :aria-label="`View review ${item.reviewId}`"
            @click="store.selectReview(item.reviewId)"
            @keydown.enter="store.selectReview(item.reviewId)"
            @keydown.space.prevent="store.selectReview(item.reviewId)"
          >
            <div class="panel-card__header">
              <strong>{{ item.reviewId }}</strong>
              <span class="review-status-badge" :class="`review-status-badge--${item.status}`">
                {{ item.status }}
              </span>
            </div>
            <h4>{{ item.title }}</h4>
            <p v-if="item.summaryPreview" class="panel-card__summary">{{ item.summaryPreview }}</p>
            <div class="panel-card__meta">
              <span>{{ item.category }}</span>
              <span>{{ item.proposedAction }}</span>
              <span>Score: {{ item.score }}</span>
              <span v-if="item.occurrenceCount > 1">×{{ item.occurrenceCount }}</span>
            </div>
          </article>

          <!-- Load more -->
          <button
            v-if="store.page.hasMore"
            type="button"
            class="panel-retry-btn review-load-more"
            @click="store.loadMoreReviews()"
          >
            Load more ({{ store.page.total - store.items.length }} remaining)
          </button>
        </div>
      </template>
    </template>
  </section>
</template>
