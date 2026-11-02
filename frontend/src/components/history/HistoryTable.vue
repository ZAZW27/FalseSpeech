<script setup>
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import StatusChip from '@/components/ui/badges/StatusChip.vue'

// rows: [{ id, sessionId, date, duration, fakePercent, meta: { label, tone } }]
// Rows are prepared by the page, so this component only renders.
defineProps({
  rows: { type: Array, default: () => [] },
})

const columns = 'grid grid-cols-[0.8fr_1.8fr_0.9fr_1.5fr_1.2fr] items-center gap-4'
</script>

<template>
  <div class="rounded-3xl border border-white/10 bg-white/[0.04]">
    <!-- Scrolls horizontally if the screen is narrow -->
    <div class="overflow-x-auto">
      <div class="min-w-[680px]" role="table" aria-label="Detection history">
        <div
          :class="[columns, 'border-b border-white/10 px-6 py-4 text-[11px] font-semibold uppercase tracking-wider text-muted']"
          role="row"
        >
          <span role="columnheader">Session ID</span>
          <span role="columnheader">Date &amp; Time</span>
          <span role="columnheader">Duration</span>
          <span role="columnheader">Fake Ratio</span>
          <span role="columnheader">Verdict</span>
        </div>

        <div
          v-for="row in rows"
          :key="row.id"
          :class="[columns, 'border-b border-white/5 px-6 py-4 text-sm transition last:border-b-0 hover:bg-white/[0.03]']"
          role="row"
        >
          <span role="cell" class="font-mono text-muted">{{ row.sessionId }}</span>
          <span role="cell" class="font-medium">{{ row.date }}</span>
          <span role="cell" class="tabular-nums text-muted">{{ row.duration }}</span>
          <span role="cell" class="flex items-center gap-3">
            <ConfidenceBar :value="row.fakePercent" :tone="row.meta.tone" height-class="h-1.5" class="max-w-[90px]" />
            <span class="text-xs font-semibold tabular-nums">{{ row.fakePercent }}%</span>
          </span>
          <span role="cell"><StatusChip :label="row.meta.label" :tone="row.meta.tone" /></span>
        </div>
      </div>
    </div>
  </div>
</template>
