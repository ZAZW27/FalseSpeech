<script setup>
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import StatusChip from '@/components/ui/badges/StatusChip.vue'

// One history item for the mobile list. Same row shape as HistoryTable.
defineProps({
  row: { type: Object, required: true },
})
</script>

<template>
  <article class="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="font-mono text-sm text-muted">{{ row.sessionId }}</p>
        <p class="mt-1 text-sm font-semibold">{{ row.date }}</p>
      </div>
      <StatusChip :label="row.meta.label" :tone="row.meta.tone" />
    </div>

    <dl class="mt-4 grid grid-cols-2 gap-4 text-sm">
      <div>
        <dt class="text-[11px] font-semibold uppercase tracking-wider text-muted">Duration</dt>
        <dd class="mt-1 tabular-nums">{{ row.duration }}</dd>
      </div>
      <div>
        <dt class="text-[11px] font-semibold uppercase tracking-wider text-muted">Fake Ratio</dt>
        <dd class="mt-1 flex items-center gap-3">
          <ConfidenceBar :value="row.fakePercent" :tone="row.meta.tone" height-class="h-1.5" class="max-w-[70px]" />
          <span class="text-xs font-semibold tabular-nums">{{ row.fakePercent }}%</span>
        </dd>
      </div>
    </dl>
  </article>
</template>
