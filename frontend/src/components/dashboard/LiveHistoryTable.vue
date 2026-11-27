<script setup>
// rows: [{ id, time, chunk, size, label, tone: 'real' | 'fake' | 'uncertain', fake }] newest first
defineProps({
  rows: { type: Array, default: () => [] },
})

const toneClass = {
  real: 'text-brand-green',
  fake: 'text-red-400',
  uncertain: 'text-secondary',
}

const columns = 'grid grid-cols-[1.3fr_0.7fr_1fr_1fr_0.9fr] items-center gap-4'
</script>

<template>
  <section class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 py-6">
    <header class="px-6">
      <h2 class="text-lg font-bold text-slate-100">Inference history</h2>
      <p class="mt-1 text-xs text-slate-400">Live results for the current session</p>
    </header>

    <!-- Scrolls in both directions on small screens -->
    <div class="mt-5 max-h-[320px] overflow-auto">
      <div class="min-w-[560px]" role="table" aria-label="Inference history">
        <div
          :class="[columns, 'sticky top-0 border-b border-back-secondary bg-back-prime px-6 py-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400']"
          role="row"
        >
          <span role="columnheader">Time</span>
          <span role="columnheader">Chunk #</span>
          <span role="columnheader">Size</span>
          <span role="columnheader">Verdict</span>
          <span role="columnheader">Fake prob</span>
        </div>

        <p v-if="!rows.length" class="px-6 py-8 text-sm text-slate-400">
          No chunks analyzed yet. Start listening to see results here.
        </p>

        <div
          v-for="row in rows"
          :key="row.id"
          :class="[columns, 'border-b border-back-secondary px-6 py-3 text-[13px] tabular-nums hover:bg-white/[0.03]']"
          role="row"
        >
          <span role="cell">{{ row.time }}</span>
          <span role="cell">#{{ row.chunk }}</span>
          <span role="cell">{{ row.size.toLocaleString() }} B</span>
          <span role="cell" :class="['font-bold', toneClass[row.tone]]">{{ row.label }}</span>
          <span role="cell">{{ (row.fake * 100).toFixed(1) }}%</span>
        </div>
      </div>
    </div>
  </section>
</template>
