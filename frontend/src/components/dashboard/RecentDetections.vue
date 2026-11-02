<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { confidenceOf, getVerdictMeta } from '@/assets/js/historyStats'
import { formatClock, formatSessionTime } from '@/assets/js/format'
import StatusChip from '@/components/ui/badges/StatusChip.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import Icon from '@/components/ui/icons/Icon.vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  limit: { type: Number, default: 5 },
})

// Newest first. The API does not send a source field, so the table has no source column.
const rows = computed(() =>
  [...props.history]
    .sort((a, b) => new Date(b.started_at) - new Date(a.started_at))
    .slice(0, props.limit)
    .map((item) => ({
      id: item.session_id,
      time: formatSessionTime(item.started_at),
      duration: formatClock(item.duration),
      meta: getVerdictMeta(item.verdict),
      confidence: confidenceOf(item),
    })),
)

const columns = 'grid grid-cols-[1.5fr_0.8fr_1.3fr_1.4fr] items-center gap-4'
</script>

<template>
  <section class="rounded-3xl border border-white/10 bg-white/[0.04] py-6">
    <header class="flex items-center justify-between px-6">
      <h2 class="text-lg font-bold">Recent detections</h2>
      <RouterLink to="/history" class="flex items-center gap-1 text-sm font-semibold text-lime-300 hover:underline">
        View all
        <Icon name="chevron-right" :size="16" />
      </RouterLink>
    </header>

    <!-- Horizontal scroll on small screens -->
    <div class="mt-5 overflow-x-auto">
      <div class="min-w-[520px]" role="table" aria-label="Recent detections">
        <div :class="[columns, 'border-b border-white/10 px-6 pb-3 text-[11px] font-semibold uppercase tracking-wider text-muted']" role="row">
          <span role="columnheader">Time</span>
          <span role="columnheader">Duration</span>
          <span role="columnheader">Verdict</span>
          <span role="columnheader">Confidence</span>
        </div>

        <p v-if="loading" class="px-6 py-8 text-sm text-muted" role="status">Loading history...</p>
        <p v-else-if="error" class="px-6 py-8 text-sm text-danger" role="alert">{{ error }}</p>
        <p v-else-if="!rows.length" class="px-6 py-8 text-sm text-muted">No detections yet. Start listening to see results here.</p>

        <template v-else>
          <div
            v-for="row in rows"
            :key="row.id"
            :class="[columns, 'border-b border-white/5 px-6 py-4 text-sm']"
            role="row"
          >
            <span role="cell" class="font-medium">{{ row.time }}</span>
            <span role="cell" class="tabular-nums text-muted">{{ row.duration }}</span>
            <span role="cell"><StatusChip :label="row.meta.label" :tone="row.meta.tone" /></span>
            <span role="cell" class="flex items-center gap-3">
              <ConfidenceBar :value="row.confidence" :tone="row.meta.tone" height-class="h-1.5" class="max-w-[90px]" />
              <span class="text-xs font-semibold tabular-nums">{{ row.confidence }}%</span>
            </span>
          </div>
        </template>
      </div>
    </div>

    <p class="mt-5 flex items-center gap-2 px-6 text-xs text-muted">
      <span class="text-muted"><Icon name="shield" :size="14" /></span>
      Only results are saved. Audio is processed in memory and never stored.
    </p>
  </section>
</template>
