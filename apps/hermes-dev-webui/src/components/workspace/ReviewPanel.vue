<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useReviewStore } from '@/stores/review'

const store = useReviewStore()

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
      <span class="panel-phase-badge" title="Read-only in Phase 1A">1A</span>
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

        <!-- Safety area -->
        <div class="review-safety">
          <span class="review-safety__badge" title="Read-only in Phase 1A">
            🔒 Read-only
          </span>
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
