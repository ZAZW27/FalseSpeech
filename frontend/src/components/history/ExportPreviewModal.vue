<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { authFetch } from '@/assets/js/api'

const FORMATS = [
  { id: 'pdf', label: 'PDF' },
  { id: 'csv', label: 'CSV' },
  { id: 'txt', label: 'TXT' },
  { id: 'md', label: 'Markdown' },
  { id: 'json', label: 'JSON' },
]

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  sessionId: { type: String, default: null },
  sessionIds: { type: Array, default: null },
  sessionTitle: { type: String, default: '' },
  filters: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['update:modelValue', 'downloaded'])

const selectedFormat = ref('pdf')
const isLoading = ref(false)
const errorMessage = ref('')
const previewBlobUrl = ref('')
const previewText = ref('')
const currentBlob = ref(null)
const currentFilename = ref('')

const modalTitle = computed(() => {
  if (props.sessionIds && props.sessionIds.length) {
    return `Export ${props.sessionIds.length} Selected Session${props.sessionIds.length === 1 ? '' : 's'}`
  }
  return props.sessionId ? `Export ${props.sessionTitle || `Session #${props.sessionId}`}` : 'Export Detection Report'
})

const revokePreviewUrl = () => {
  if (previewBlobUrl.value) {
    URL.revokeObjectURL(previewBlobUrl.value)
    previewBlobUrl.value = ''
  }
}

const buildQuery = (format) => {
  const params = new URLSearchParams({ format })
  if (props.sessionIds && props.sessionIds.length) {
    params.set('session_ids', props.sessionIds.join(','))
  } else if (props.sessionId) {
    params.set('session_id', String(props.sessionId))
  } else {
    const f = props.filters || {}
    if (f.verdict && f.verdict !== 'all') params.set('verdict', f.verdict)
    if (f.source && f.source !== 'all') params.set('source', f.source)
    if (f.search) params.set('search', f.search)
    if (f.startDate) params.set('start_date', new Date(f.startDate).toISOString())
    if (f.endDate) params.set('end_date', new Date(f.endDate).toISOString())
  }
  return params.toString()
}

const loadPreview = async () => {
  if (!props.modelValue) return
  isLoading.value = true
  errorMessage.value = ''
  revokePreviewUrl()
  previewText.value = ''
  currentBlob.value = null

  const fmt = selectedFormat.value
  try {
    const res = await authFetch(`/api/history/export?${buildQuery(fmt)}`)
    if (!res.ok) throw new Error(`Export preview failed (${res.status})`)

    const blob = await res.blob()
    const disposition = res.headers.get('content-disposition') || ''
    const match = disposition.match(/filename="?([^"]+)"?/i)
    currentFilename.value =
      match?.[1] || `FalseSpeech-HR-${props.sessionId ? `session-${props.sessionId}` : 'report'}.${fmt}`
    currentBlob.value = blob

    if (fmt === 'pdf') {
      previewBlobUrl.value = URL.createObjectURL(blob)
    } else {
      previewText.value = await blob.text()
    }
  } catch {
    errorMessage.value = 'Could not generate preview. Please try again.'
  } finally {
    isLoading.value = false
  }
}

const close = () => {
  emit('update:modelValue', false)
}

const downloadCurrent = () => {
  if (!currentBlob.value) return
  const url = previewBlobUrl.value || URL.createObjectURL(currentBlob.value)
  const link = document.createElement('a')
  link.href = url
  link.download = currentFilename.value || `FalseSpeech-HR.${selectedFormat.value}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  if (!previewBlobUrl.value) URL.revokeObjectURL(url)
  emit('downloaded', currentFilename.value)
}

const onKeydown = (e) => {
  if (e.key === 'Escape' && props.modelValue) close()
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selectedFormat.value = 'pdf'
      window.addEventListener('keydown', onKeydown)
      loadPreview()
    } else {
      window.removeEventListener('keydown', onKeydown)
      revokePreviewUrl()
      previewText.value = ''
      currentBlob.value = null
    }
  },
)

watch(selectedFormat, () => {
  if (props.modelValue) loadPreview()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  revokePreviewUrl()
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/65 p-4 backdrop-blur-xs"
      role="dialog"
      aria-modal="true"
      :aria-label="modalTitle"
      @click.self="close"
    >
      <div class="flex max-h-[90vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-white/15 bg-back-prime shadow-2xl">
        <!-- Minimal Google Docs-style Header -->
        <div class="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <div>
            <h2 class="text-base font-bold text-white">{{ modalTitle }}</h2>
            <p class="mt-0.5 text-xs text-slate-400">Choose a format and preview your report before downloading.</p>
          </div>
          <button
            type="button"
            class="rounded-lg px-2.5 py-1 text-lg leading-none text-slate-400 transition hover:bg-white/10 hover:text-white"
            aria-label="Close export modal"
            @click="close"
          >
            &times;
          </button>
        </div>

        <!-- Clean Format Tabs (no icons) -->
        <div class="flex flex-wrap items-center gap-1.5 border-b border-white/10 bg-[#1a202c]/70 px-6 py-3">
          <button
            v-for="fmt in FORMATS"
            :key="fmt.id"
            type="button"
            :class="[
              'rounded-lg px-3.5 py-1.5 text-xs font-semibold transition',
              selectedFormat === fmt.id
                ? 'bg-white text-back-prime'
                : 'text-slate-300 hover:bg-white/10 hover:text-white',
            ]"
            @click="selectedFormat = fmt.id"
          >
            {{ fmt.label }}
          </button>
        </div>

        <!-- Live Preview Body -->
        <div class="flex-1 overflow-auto bg-[#151a24] p-5">
          <div v-if="isLoading" class="flex h-[56vh] flex-col gap-3">
            <div class="skeleton-shimmer h-10 w-1/3 rounded-lg" />
            <div class="skeleton-shimmer flex-1 rounded-xl" />
          </div>

          <div
            v-else-if="errorMessage"
            class="flex h-[40vh] flex-col items-center justify-center gap-3 text-center"
          >
            <p class="text-sm text-red-400">{{ errorMessage }}</p>
            <button
              type="button"
              class="rounded-lg border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold text-white hover:bg-white/10"
              @click="loadPreview"
            >
              Retry Preview
            </button>
          </div>

          <iframe
            v-else-if="selectedFormat === 'pdf' && previewBlobUrl"
            :src="previewBlobUrl"
            title="PDF Export Preview"
            class="h-[58vh] w-full rounded-xl border border-white/10 bg-white"
          />

          <pre
            v-else
            class="max-h-[58vh] overflow-auto rounded-xl border border-white/10 bg-[#0f141d] p-4 font-sans text-xs leading-relaxed text-slate-200 whitespace-pre-wrap break-words"
          >{{ previewText || 'No data to preview.' }}</pre>
        </div>

        <!-- Simple Footer -->
        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-white/10 px-6 py-4">
          <span class="truncate text-xs text-slate-400">{{ currentFilename || 'Preparing file...' }}</span>
          <div class="flex items-center gap-2.5">
            <button
              type="button"
              class="rounded-xl border border-white/15 px-4 py-2 text-xs font-semibold text-slate-300 transition hover:bg-white/10 hover:text-white"
              @click="close"
            >
              Cancel
            </button>
            <button
              type="button"
              :disabled="isLoading || !currentBlob"
              class="rounded-xl border border-brand-green/40 bg-[#2f6b5e] px-5 py-2 text-xs font-bold text-slate-100 transition hover:bg-[#387c6d] disabled:opacity-40"
              @click="downloadCurrent"
            >
              Download {{ selectedFormat.toUpperCase() }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
