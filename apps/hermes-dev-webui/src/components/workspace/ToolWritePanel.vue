<script setup lang="ts">
import { computed } from 'vue'
import { useToolWriteStore } from '@/stores/toolWrite'
import type { WriteToolId } from '@/types/api/toolWrite'

const store = useToolWriteStore()

const TOOL_LABELS: Record<WriteToolId, string> = {
  dev_sandbox_file_write: 'Sandbox File Write',
  dev_sandbox_file_append: 'Sandbox File Append',
  dev_sandbox_file_patch: 'Sandbox File Patch',
  dev_sandbox_file_readback: 'Sandbox File Readback',
}

const targetPathError = computed(() => {
  if (!store.targetPath) return ''
  if (store.targetPath.startsWith('/') || store.targetPath.startsWith('~') || store.targetPath.startsWith('\\')) {
    return 'Absolute paths are not allowed — use a sandbox-relative path.'
  }
  if (store.targetPath.includes('..')) return 'Path traversal (..) is not allowed.'
  if (store.targetPath.includes('\x00')) return 'Invalid characters in path.'
  const lower = store.targetPath.toLowerCase()
  for (const bad of ['.env', '.claude', '.git', '.db', '.sqlite', '.jsonl', '.log', 'test-results', 'playwright-report', 'node_modules']) {
    if (lower.includes(bad)) return `Forbidden target: ${bad}`
  }
  return ''
})

const unsafeTarget = computed(() => targetPathError.value !== '' || store.targetPathUnsafe)
</script>

<template>
  <section class="tool-write" aria-label="Controlled write tools">
    <header class="tool-write__header">
      <h3>Controlled Write Tools</h3>
      <p>Dev-sandbox write MVP — preview, confirm, then execute inside the sandbox only.</p>
    </header>

    <dl class="tool-write__flags">
      <div><dt>Sandbox only</dt><dd>yes</dd></div>
      <div><dt>Read-only</dt><dd>false</dd></div>
      <div><dt>Write required</dt><dd>true</dd></div>
      <div><dt>External side effects</dt><dd>false</dd></div>
      <div><dt>Local side effects</dt><dd>true</dd></div>
      <div><dt>Requires confirmation</dt><dd>true</dd></div>
      <div><dt>Write enablement</dt><dd>HERMES_TOOL_WRITE_EXECUTION_ENABLED</dd></div>
    </dl>

    <div class="tool-write__field">
      <label for="write-tool">Write tool</label>
      <select id="write-tool" :value="store.toolId" @change="store.setToolId(($event.target as HTMLSelectElement).value as WriteToolId)">
        <option v-for="t in store.selectableTools" :key="t" :value="t">{{ TOOL_LABELS[t] }}</option>
      </select>
    </div>

    <div class="tool-write__field">
      <label for="write-target">Target relative path (sandbox only)</label>
      <input
        id="write-target"
        type="text"
        :value="store.targetPath"
        placeholder="notes/example.md"
        :aria-invalid="unsafeTarget"
        @input="store.setTargetPath(($event.target as HTMLInputElement).value)"
      />
      <p v-if="unsafeTarget" class="tool-write__error">{{ targetPathError || 'Unsafe target path.' }}</p>
    </div>

    <div v-if="store.needsContent" class="tool-write__field">
      <label for="write-content">Content (UTF-8 text)</label>
      <textarea
        id="write-content"
        :value="store.content"
        rows="5"
        @input="store.setContent(($event.target as HTMLTextAreaElement).value)"
      ></textarea>
    </div>

    <template v-if="store.needsPatch">
      <div class="tool-write__field">
        <label for="write-search">Search (exact, unique match)</label>
        <input id="write-search" type="text" :value="store.searchFragment" @input="store.setSearchFragment(($event.target as HTMLInputElement).value)" />
      </div>
      <div class="tool-write__field">
        <label for="write-replace">Replace</label>
        <input id="write-replace" type="text" :value="store.replaceFragment" @input="store.setReplaceFragment(($event.target as HTMLInputElement).value)" />
      </div>
    </template>

    <div class="tool-write__actions">
      <button
        type="button"
        class="tool-write__btn tool-write__btn--primary"
        :disabled="!store.canPreview || unsafeTarget"
        @click="store.runPreview()"
      >
        Dry-run preview
      </button>
      <button
        type="button"
        class="tool-write__btn"
        :disabled="!store.canExecute"
        @click="store.runExecute()"
      >
        Execute write
      </button>
    </div>

    <p v-if="store.error" class="tool-write__error">{{ store.error }}</p>

    <label v-if="store.preview && !store.preview.blocked" class="tool-write__confirm">
      <input
        type="checkbox"
        :checked="store.explicitConfirmed"
        @change="store.setExplicitConfirmed(($event.target as HTMLInputElement).checked)"
      />
      I confirm this write inside the dev sandbox.
    </label>

    <div v-if="store.preview" class="tool-write__preview">
      <h4>Preview</h4>
      <dl class="tool-write__kv">
        <div><dt>Operation</dt><dd>{{ store.preview.operation }}</dd></div>
        <div><dt>Target</dt><dd>{{ store.preview.targetRelativePath }}</dd></div>
        <div><dt>Sandbox</dt><dd>{{ store.preview.sandboxRootLabel }}</dd></div>
        <div><dt>Before exists</dt><dd>{{ store.preview.beforeExists }}</dd></div>
        <div><dt>Before hash</dt><dd>{{ store.preview.beforeHash ?? '—' }}</dd></div>
        <div><dt>After hash</dt><dd>{{ store.preview.afterHash ?? '—' }}</dd></div>
        <div><dt>Content digest</dt><dd>{{ store.preview.contentDigest ?? '—' }}</dd></div>
        <div><dt>Argument digest</dt><dd>{{ store.preview.argumentDigest }}</dd></div>
      </dl>
      <div v-if="store.preview.diffPreview" class="tool-write__diff">
        <h5>Diff preview</h5>
        <pre>{{ store.preview.diffPreview }}</pre>
      </div>
      <div class="tool-write__rollback">
        <h5>Rollback preview</h5>
        <p>{{ store.preview.rollbackPreview }}</p>
      </div>
      <p v-for="w in store.preview.warnings" :key="w" class="tool-write__warning">⚠ {{ w }}</p>
      <p v-if="store.preview.blocked" class="tool-write__error">Blocked: {{ store.preview.blockedReason }}</p>
    </div>

    <div v-if="store.executeResult" class="tool-write__result">
      <h4>Result</h4>
      <dl class="tool-write__kv">
        <div><dt>Status</dt><dd>{{ store.executeResult.status }}</dd></div>
        <div><dt>Operation</dt><dd>{{ store.executeResult.operation }}</dd></div>
        <div><dt>Target</dt><dd>{{ store.executeResult.targetRelativePath }}</dd></div>
        <div><dt>Bytes written</dt><dd>{{ store.executeResult.bytesWritten }}</dd></div>
        <div><dt>Before hash</dt><dd>{{ store.executeResult.beforeHash ?? '—' }}</dd></div>
        <div><dt>After hash</dt><dd>{{ store.executeResult.afterHash ?? '—' }}</dd></div>
        <div><dt>Rollback available</dt><dd>{{ store.executeResult.rollbackAvailable }}</dd></div>
        <div><dt>Rollback id</dt><dd>{{ store.executeResult.rollbackId ?? '—' }}</dd></div>
        <div><dt>Pre-exec audit</dt><dd>{{ store.executeResult.preExecutionAuditId ?? '—' }}</dd></div>
        <div><dt>Post-exec audit</dt><dd>{{ store.executeResult.postExecutionAuditId ?? '—' }}</dd></div>
        <div><dt>External network</dt><dd>{{ store.executeResult.externalNetworkCalled }}</dd></div>
      </dl>
      <div v-if="store.executeResult.readback" class="tool-write__readback">
        <h5>Readback</h5>
        <p>Exists: {{ store.executeResult.readback.exists }} · {{ store.executeResult.readback.sizeBytes }} bytes</p>
        <pre>{{ store.executeResult.readback.snippet }}</pre>
      </div>
      <p v-if="store.executeResult.blockedReason" class="tool-write__error">Blocked: {{ store.executeResult.blockedReason }}</p>
    </div>

    <!-- Phase 2C-H1: rollback execution -->
    <div class="tool-write__rollback">
      <h4>Rollback</h4>
      <div class="tool-write__field">
        <label for="write-rollback-id">Rollback manifest id</label>
        <input
          id="write-rollback-id"
          type="text"
          :value="store.rollbackId"
          placeholder="wrbk_…"
          @input="store.setRollbackId(($event.target as HTMLInputElement).value)"
        />
      </div>
      <div class="tool-write__actions">
        <button
          type="button"
          class="tool-write__btn"
          :disabled="!store.canRollbackPreview"
          @click="store.runRollbackPreview()"
        >
          Preview rollback
        </button>
        <button
          type="button"
          class="tool-write__btn tool-write__btn--primary"
          :disabled="!store.canRollbackExecute"
          @click="store.runRollbackExecute()"
        >
          Execute rollback
        </button>
      </div>

      <div v-if="store.rollbackPreview" class="tool-write__preview">
        <h5>Rollback preview</h5>
        <dl class="tool-write__kv">
          <div><dt>Restore mode</dt><dd>{{ store.rollbackPreview.restoreMode }}</dd></div>
          <div><dt>Target</dt><dd>{{ store.rollbackPreview.targetRelativePath }}</dd></div>
          <div><dt>Current hash</dt><dd>{{ store.rollbackPreview.currentHash ? store.rollbackPreview.currentHash.slice(0, 12) + '…' : '—' }}</dd></div>
          <div><dt>Hash check</dt><dd>{{ store.rollbackPreview.currentHash === store.rollbackPreview.expectedCurrentHash ? 'match' : 'mismatch' }}</dd></div>
          <div><dt>Token scope</dt><dd>{{ store.rollbackPreview.confirmationTokenScope ?? '—' }}</dd></div>
        </dl>
        <p>{{ store.rollbackPreview.restorePreview }}</p>
        <label v-if="!store.rollbackPreview.blocked" class="tool-write__confirm">
          <input
            type="checkbox"
            :checked="store.rollbackConfirmed"
            @change="store.setRollbackConfirmed(($event.target as HTMLInputElement).checked)"
          />
          I confirm this rollback inside the dev sandbox.
        </label>
        <p v-if="store.rollbackPreview.blocked" class="tool-write__error">Blocked: {{ store.rollbackPreview.blockedReason }}</p>
      </div>

      <div v-if="store.rollbackResult" class="tool-write__result">
        <h5>Rollback result</h5>
        <dl class="tool-write__kv">
          <div><dt>Status</dt><dd>{{ store.rollbackResult.status }}</dd></div>
          <div><dt>Restore mode</dt><dd>{{ store.rollbackResult.restoreMode }}</dd></div>
          <div><dt>Final hash</dt><dd>{{ store.rollbackResult.finalHash ?? '— (deleted)' }}</dd></div>
          <div><dt>Token state</dt><dd>{{ store.rollbackTokenState }}</dd></div>
          <div><dt>Pre-exec audit</dt><dd>{{ store.rollbackResult.preExecutionAuditId ?? '—' }}</dd></div>
          <div><dt>Post-exec audit</dt><dd>{{ store.rollbackResult.postExecutionAuditId ?? '—' }}</dd></div>
        </dl>
        <p v-if="store.rollbackResult.blockedReason" class="tool-write__error">Blocked: {{ store.rollbackResult.blockedReason }}</p>
        <p v-if="store.rollbackTokenState === 'replay_blocked'" class="tool-write__warning">⚠ Replay blocked — this confirmation token was already used.</p>
        <p v-else-if="store.rollbackTokenState === 'expired'" class="tool-write__warning">⚠ Confirmation token expired — re-run the preview.</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.tool-write {
  display: flex;
  flex-direction: column;
  gap: var(--space-3, 12px);
  padding: var(--space-3, 12px);
  font-size: var(--font-size-md, 0.875rem);
  color: var(--color-text-primary, #e4e4e8);
}
.tool-write__header h3 { margin: 0; font-size: var(--font-size-lg, 1rem); }
.tool-write__header p { margin: 2px 0 0; color: var(--color-text-secondary, #a0a0aa); font-size: var(--font-size-sm, 0.8125rem); }
.tool-write__flags {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-1, 4px) var(--space-2, 8px);
  margin: 0;
  font-size: var(--font-size-xs, 0.75rem);
}
.tool-write__flags div { display: flex; justify-content: space-between; gap: var(--space-2, 8px); }
.tool-write__flags dt { color: var(--color-text-secondary, #a0a0aa); }
.tool-write__field { display: flex; flex-direction: column; gap: 4px; }
.tool-write__field label { font-size: var(--font-size-sm, 0.8125rem); color: var(--color-text-secondary, #a0a0aa); }
.tool-write__field input,
.tool-write__field select,
.tool-write__field textarea {
  background: var(--color-panel-bg, #26262e);
  border: 1px solid var(--color-border, #3a3a44);
  border-radius: var(--radius-sm, 4px);
  color: inherit;
  padding: 6px 8px;
  font: inherit;
}
.tool-write__field textarea { resize: vertical; font-family: var(--font-mono, monospace); }
.tool-write__actions { display: flex; gap: var(--space-2, 8px); }
.tool-write__btn {
  border: 1px solid var(--color-border, #3a3a44);
  background: var(--color-panel-bg, #26262e);
  color: inherit;
  padding: 6px 12px;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
  font: inherit;
}
.tool-write__btn--primary { background: var(--color-accent, #7c8adb); color: #fff; border-color: transparent; }
.tool-write__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tool-write__confirm { display: flex; align-items: center; gap: var(--space-2, 8px); font-size: var(--font-size-sm, 0.8125rem); }
.tool-write__error { color: var(--color-error, #e5656b); font-size: var(--font-size-sm, 0.8125rem); }
.tool-write__warning { color: var(--color-warning, #d4a843); font-size: var(--font-size-sm, 0.8125rem); }
.tool-write__preview,
.tool-write__result {
  border: 1px solid var(--color-border, #3a3a44);
  border-radius: var(--radius-sm, 4px);
  padding: var(--space-2, 8px);
  background: var(--color-panel-bg, #26262e);
}
.tool-write__preview h4,
.tool-write__result h4 { margin: 0 0 var(--space-2, 8px); font-size: var(--font-size-md, 0.875rem); }
.tool-write__kv {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 2px var(--space-2, 8px);
  margin: 0 0 var(--space-2, 8px);
  font-size: var(--font-size-xs, 0.75rem);
}
.tool-write__kv div { display: flex; justify-content: space-between; gap: var(--space-2, 8px); }
.tool-write__kv dt { color: var(--color-text-secondary, #a0a0aa); }
.tool-write__diff pre,
.tool-write__readback pre {
  margin: 0;
  padding: var(--space-2, 8px);
  background: var(--color-app-bg, #1c1c22);
  border-radius: var(--radius-sm, 4px);
  font-family: var(--font-mono, monospace);
  font-size: var(--font-size-xs, 0.75rem);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.tool-write__rollback h5,
.tool-write__diff h5,
.tool-write__readback h5 { margin: var(--space-2, 8px) 0 4px; font-size: var(--font-size-sm, 0.8125rem); }
</style>
