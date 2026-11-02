<script setup>
import { computed } from 'vue'

// Probabilities from the WebSocket, 0 to 1. Null before the first result.
const props = defineProps({
  fake: { type: Number, default: null },
  real: { type: Number, default: null },
})

const toPercent = (value) =>
  value === null || !Number.isFinite(value) ? null : Math.round(Math.min(1, Math.max(0, value)) * 100)

const bars = computed(() => [
  { id: 'fake', label: 'Fake', percent: toPercent(props.fake), textClass: 'text-danger', fillClass: 'bg-gradient-to-t from-danger to-[#ff8a9f]' },
  { id: 'real', label: 'Real', percent: toPercent(props.real), textClass: 'text-brand-green', fillClass: 'bg-gradient-to-t from-brand-green to-lime-300' },
])
</script>

<template>
  <section class="flex flex-col rounded-3xl border border-white/10 bg-white/[0.04] p-6">
    <h2 class="text-lg font-bold">Confidence</h2>
    <p class="mt-1 text-xs text-muted">Probability for the latest segment</p>

    <div class="mt-4 flex flex-1 items-end justify-center gap-10 sm:gap-16">
      <div v-for="bar in bars" :key="bar.id" class="flex flex-col items-center gap-3">
        <span :class="['text-2xl font-extrabold tabular-nums', bar.textClass]">
          {{ bar.percent === null ? '--' : `${bar.percent}%` }}
        </span>

        <div
          class="relative h-40 w-12 overflow-hidden rounded-2xl bg-white/10"
          role="progressbar"
          :aria-label="`${bar.label} probability`"
          :aria-valuenow="bar.percent ?? 0"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div
            :class="['absolute inset-x-0 bottom-0 rounded-2xl transition-all duration-500 ease-out', bar.fillClass]"
            :style="{ height: `${bar.percent ?? 0}%` }"
          />
        </div>

        <span class="text-sm font-medium text-white/80">{{ bar.label }}</span>
      </div>
    </div>
  </section>
</template>
