<script setup>
import { computed, ref, watch } from 'vue'
import { formatDateTime, formatSessionDuration, ratioToPercent } from '@/assets/js/format'
import { getVerdictMeta } from '@/assets/js/historyStats'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import StatusChip from '@/components/ui/badges/StatusChip.vue'
import SessionRiskTimeline from '@/components/history/SessionRiskTimeline.vue'

const props = defineProps({
  session: { type: Object, required: true },
  expanded: { type: Boolean, default: false },
  segments: { type: Array, default: null }, // null = not yet loaded
  loadingSegments: { type: Boolean, default: false },
})

const emit = defineEmits(['toggle', 'save-meta', 'delete', 'open-export'])

const editingMeta = ref(false)
const draftTitle = ref('')
const draftNotes = ref('')
const savingMeta = ref(false)
const confirmDelete = ref(false)
const copied = ref(false)
const chunkFilter = ref('all') // 'all' | 'fake' | 'real'
const selectedChunkId = ref(null)

const selectChunkFromTimeline = (chunkKey) => {
  selectedChunkId.value = selectedChunkId.value === chunkKey ? null : chunkKey
  if (chunkFilter.value !== 'all') chunkFilter.value = 'all'
}

const meta = computed(() => getVerdictMeta(props.session.verdict))
const fakePercent = computed(() => ratioToPercent(props.session.fake_ratio))
const peakPercent = computed(() => ratioToPercent(props.session.max_fake_prob ?? props.session.fake_ratio))
const displayTitle = computed(() => (props.session.title || '').trim() || `Session #${props.session.session_id}`)
const dateLabel = computed(() => formatDateTime(props.session.started_at))
const durationLabel = computed(() => formatSessionDuration(props.session.duration))
const sourceLabel = computed(() => String(props.session.source || 'web').toUpperCase())

const filteredSegments = computed(() => {
  const list = props.segments || []
  if (chunkFilter.value === 'fake') return list.filter((s) => s.is_fake)
  if (chunkFilter.value === 'real') return list.filter((s) => !s.is_fake)
  return list
})

watch(
  () => props.session,
  (s) => {
    if (!editingMeta.value) {
      draftTitle.value = s?.title || ''
      draftNotes.value = s?.notes || ''
    }
  },
  { immediate: true },
)

const startEdit = () => {
  draftTitle.value = props.session.title || ''
  draftNotes.value = props.session.notes || ''
  editingMeta.value = true
}

const cancelEdit = () => {
  editingMeta.value = false
}

const submitMeta = async () => {
  savingMeta.value = true
  try {
    await emit('save-meta', {
      sessionId: props.session.session_id,
      title: draftTitle.value,
      notes: draftNotes.value,
    })
    editingMeta.value = false
  } finally {
    savingMeta.value = false
  }
}

const copySummary = async () => {
  const lines = [
    `False Speech HR Voice Verification Summary`,
    `Session: ${displayTitle.value} (#${props.session.session_id})`,
    `Date: ${dateLabel.value} | Duration: ${durationLabel.value} | Source: ${sourceLabel.value}`,
    `Verdict: ${meta.value.label.toUpperCase()} | Avg AI Risk: ${fakePercent.value}% (Peak: ${peakPercent.value}%)`,
    `Chunks: ${props.session.total_chunks} total (${props.session.fake_count} AI flagged, ${props.session.real_count} Human verified)`,
  ]
  if (props.session.notes) lines.push(`HR Notes: ${props.session.notes}`)
  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    // Clipboard unavailable
  }
}

const formatChunkTime = (iso) => {
  if (!iso) return '-'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '-'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <article
    :class="[
      'rounded-2xl border-2 bg-back-secondary/40 transition-colors duration-300',
      expanded ? 'border-white/25 bg-back-secondary/55' : 'border-back-secondary hover:border-white/20',
    ]"
  >
    <!-- Session Summary Header (click to expand/collapse chunks dropdown) -->
    <button
      type="button"
      class="flex w-full flex-col gap-3 px-5 py-4 text-left transition hover:bg-white/[0.02] lg:flex-row lg:items-center lg:justify-between"
      :aria-expanded="expanded"
      @click="$emit('toggle', session.session_id)"
    >
      <div class="flex min-w-0 items-start gap-3.5 lg:items-center">
        <span
          :class="[
            'mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-back-prime/80 text-slate-300 transition-transform duration-500 lg:mt-0',
            expanded ? 'rotate-180 border-white/25 text-white' : '',
          ]"
          aria-hidden="true"
        >
          <svg viewBox="0 0 20 20" class="size-4 fill-current">
            <path
              fill-rule="evenodd"
              d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
              clip-rule="evenodd"
            />
          </svg>
        </span>

        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="truncate text-sm font-bold text-white sm:text-base">{{ displayTitle }}</h3>
            <span class="rounded-md bg-white/10 px-1.5 py-0.5 text-[11px] font-semibold tabular-nums text-slate-300">
              #{{ session.session_id }}
            </span>
            <span
              class="rounded-md border border-white/10 bg-back-prime/70 px-1.5 py-0.5 text-[10px] font-semibold tracking-wider text-slate-400"
            >
              {{ sourceLabel }}
            </span>
            <span
              v-if="session.notes"
              class="rounded-md border border-white/15 bg-white/10 px-1.5 py-0.5 text-[10px] font-semibold text-white"
            >
              HR Note
            </span>
          </div>

          <div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
            <span>{{ dateLabel }}</span>
            <span aria-hidden="true">&bull;</span>
            <span class="tabular-nums">{{ durationLabel }}</span>
            <span aria-hidden="true">&bull;</span>
            <span class="tabular-nums font-medium text-white">
              {{ session.total_chunks }} chunk{{ session.total_chunks === 1 ? '' : 's' }}
              <span class="font-normal text-slate-400">
                ({{ session.fake_count }} AI / {{ session.real_count }} Human)
              </span>
            </span>
          </div>
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-4 pl-11 lg:justify-end lg:pl-0">
        <div class="flex items-center gap-2.5">
          <div class="w-24">
            <ConfidenceBar :value="fakePercent" :tone="meta.tone" height-class="h-1.5" />
          </div>
          <div class="text-right">
            <p class="text-xs font-bold tabular-nums text-white">{{ fakePercent }}% AI</p>
            <p class="text-[10px] tabular-nums text-slate-400">Peak {{ peakPercent }}%</p>
          </div>
        </div>

        <StatusChip :label="meta.label" :tone="meta.tone" />
      </div>
    </button>

    <!-- Smooth Dropdown Body: HR Metadata + Export Modal Trigger + Chunks Table -->
    <div
      :class="[
        'grid transition-[grid-template-rows,opacity] duration-500 ease-[cubic-bezier(0.22,1,0.36,1)]',
        expanded ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0 pointer-events-none',
      ]"
    >
      <div class="overflow-hidden">
        <div class="border-t border-white/10 bg-back-prime/45 px-5 py-4">
          <!-- HR Toolbar -->
          <div class="flex flex-col gap-3 border-b border-white/10 pb-4 lg:flex-row lg:items-start lg:justify-between">
            <div class="min-w-0 flex-1">
              <div v-if="!editingMeta" class="flex flex-col gap-1">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Candidate / Session Label:
                  </span>
                  <span class="text-xs font-semibold text-white">{{ displayTitle }}</span>
                  <button
                    type="button"
                    class="rounded-md border border-white/15 bg-white/5 px-2 py-0.5 text-[11px] font-semibold text-white transition hover:bg-white/15"
                    @click="startEdit"
                  >
                    Edit Label &amp; Notes
                  </button>
                </div>
                <p v-if="session.notes" class="mt-0.5 text-xs leading-relaxed text-slate-300">
                  <span class="font-semibold text-slate-400">HR Notes:</span> {{ session.notes }}
                </p>
                <p v-else class="text-[11px] italic text-slate-400">
                  No HR notes yet. Add candidate name, role, or review remarks for your records.
                </p>
              </div>

              <form v-else class="flex flex-col gap-2.5 rounded-xl border border-white/15 bg-back-prime/80 p-3" @submit.prevent="submitMeta">
                <div class="grid gap-2.5 sm:grid-cols-2">
                  <div>
                    <label class="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                      Session / Candidate Title
                    </label>
                    <input
                      v-model="draftTitle"
                      type="text"
                      maxlength="160"
                      placeholder="e.g. Interview: Sarah Chen (Frontend)"
                      class="mt-1 h-9 w-full rounded-lg border border-white/15 bg-white/5 px-3 text-xs text-white placeholder:text-slate-500 focus:border-brand-green focus:outline-none"
                    />
                  </div>
                  <div>
                    <label class="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                      HR Notes / Audit Remarks
                    </label>
                    <input
                      v-model="draftNotes"
                      type="text"
                      maxlength="2000"
                      placeholder="e.g. Flagged voice anomaly during technical Q&A"
                      class="mt-1 h-9 w-full rounded-lg border border-white/15 bg-white/5 px-3 text-xs text-white placeholder:text-slate-500 focus:border-brand-green focus:outline-none"
                    />
                  </div>
                </div>
                <div class="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    class="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-slate-300 transition hover:bg-white/5"
                    @click="cancelEdit"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    :disabled="savingMeta"
                    class="rounded-lg bg-brand-green px-3 py-1.5 text-xs font-bold text-back-prime transition hover:brightness-105 disabled:opacity-50"
                  >
                    {{ savingMeta ? 'Saving...' : 'Save' }}
                  </button>
                </div>
              </form>
            </div>

            <!-- Clean Action Buttons -->
            <div class="flex flex-wrap items-center gap-2">
              <button
                type="button"
                class="rounded-lg border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-white/15"
                @click="copySummary"
              >
                {{ copied ? 'Copied' : 'Copy Summary' }}
              </button>

              <button
                type="button"
                class="rounded-lg border border-brand-green/40 bg-[#2f6b5e] px-3 py-1.5 text-xs font-bold text-slate-100 transition hover:bg-[#387c6d]"
                @click="$emit('open-export', { sessionId: session.session_id, title: displayTitle })"
              >
                Export
              </button>

              <template v-if="!confirmDelete">
                <button
                  type="button"
                  class="rounded-lg border border-red-400/25 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 transition hover:border-red-400/60 hover:bg-red-500/20"
                  @click="confirmDelete = true"
                >
                  Delete
                </button>
              </template>
              <template v-else>
                <button
                  type="button"
                  class="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-bold text-white transition hover:bg-red-500"
                  @click="$emit('delete', session.session_id); confirmDelete = false"
                >
                  Confirm Delete
                </button>
                <button
                  type="button"
                  class="rounded-lg border border-white/15 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-white/5"
                  @click="confirmDelete = false"
                >
                  Cancel
                </button>
              </template>
            </div>
          </div>

          <!-- Session Risk Timeline Chart -->
          <SessionRiskTimeline
            v-if="!loadingSegments && segments && segments.length"
            :segments="segments"
            :selected-chunk-id="selectedChunkId"
            @select-chunk="selectChunkFromTimeline"
          />

          <!-- Chunks Section Header + Filter -->
          <div class="mt-4 flex flex-wrap items-center justify-between gap-2">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              Recorded Audio Chunks ({{ filteredSegments.length }})
            </p>
            <div class="flex items-center gap-1 rounded-lg border border-white/10 bg-back-prime/80 p-0.5 text-[11px]">
              <button
                v-for="opt in [
                  { value: 'all', label: 'All' },
                  { value: 'fake', label: 'AI Flagged' },
                  { value: 'real', label: 'Human' },
                ]"
                :key="opt.value"
                type="button"
                :class="[
                  'rounded-md px-2.5 py-1 font-semibold transition',
                  chunkFilter === opt.value
                    ? 'bg-white text-back-prime'
                    : 'text-slate-400 hover:text-white',
                ]"
                @click="chunkFilter = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <!-- Loading Skeleton for Chunks -->
          <div v-if="loadingSegments" class="mt-3 flex flex-col gap-2">
            <div v-for="i in 3" :key="i" class="skeleton-shimmer h-10 w-full rounded-xl" />
          </div>

          <!-- Empty Chunks -->
          <p v-else-if="!filteredSegments.length" class="mt-3 rounded-xl border border-white/10 bg-back-prime/50 px-4 py-6 text-center text-xs text-slate-400">
            No chunks match this filter in this session.
          </p>

          <!-- Chunks Table -->
          <div v-else class="mt-3 overflow-x-auto rounded-xl border border-white/10 bg-back-prime/70">
            <table class="w-full min-w-[540px] text-left text-xs">
              <thead>
                <tr class="border-b border-white/10 text-[10px] font-semibold uppercase tracking-wider text-slate-400">
                  <th class="px-4 py-2.5">Chunk #</th>
                  <th class="px-4 py-2.5">Time</th>
                  <th class="px-4 py-2.5">Duration</th>
                  <th class="px-4 py-2.5">Fake Probability</th>
                  <th class="px-4 py-2.5">Real Probability</th>
                  <th class="px-4 py-2.5 text-right">Verdict</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="seg in filteredSegments"
                  :key="seg.id ?? seg.offset"
                  :class="[
                    'border-b border-white/5 transition last:border-b-0 hover:bg-white/[0.04]',
                    selectedChunkId === (seg.id ?? seg.offset) ? 'bg-white/[0.08]' : '',
                  ]"
                  @click="selectedChunkId = seg.id ?? seg.offset"
                >
                  <td class="px-4 py-2.5 tabular-nums text-slate-300">#{{ seg.offset }}</td>
                  <td class="px-4 py-2.5 tabular-nums text-slate-300">{{ formatChunkTime(seg.recorded_at) }}</td>
                  <td class="px-4 py-2.5 tabular-nums text-slate-300">
                    {{ seg.duration_s ? `${Number(seg.duration_s).toFixed(1)}s` : '-' }}
                  </td>
                  <td class="px-4 py-2.5">
                    <div class="flex items-center gap-2.5">
                      <ConfidenceBar
                        :value="ratioToPercent(seg.fake_prob)"
                        :tone="seg.is_fake ? 'danger' : 'success'"
                        height-class="h-1.5"
                        class="w-20"
                      />
                      <span class="font-semibold tabular-nums text-white">{{ ratioToPercent(seg.fake_prob) }}%</span>
                    </div>
                  </td>
                  <td class="px-4 py-2.5 tabular-nums text-slate-300">
                    {{ ratioToPercent(seg.real_prob ?? (1 - seg.fake_prob)) }}%
                  </td>
                  <td class="px-4 py-2.5 text-right">
                    <StatusChip
                      :label="seg.is_fake ? 'AI / Fake' : 'Human'"
                      :tone="seg.is_fake ? 'danger' : 'success'"
                    />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </article>
</template>
