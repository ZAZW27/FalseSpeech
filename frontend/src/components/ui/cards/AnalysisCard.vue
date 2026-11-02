<script setup>
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import { getTone } from '@/assets/js/tone'

defineProps({
  result: { type: Object, required: true },
})
</script>

<template>
  <article
    class="w-full rounded-2xl border border-white/15 bg-white/5 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.35)] backdrop-blur-md"
  >
    <p class="text-[11px] font-semibold uppercase tracking-[0.2em] text-lime-400">Live analysis</p>

    <div class="mt-4 flex items-end gap-4">
      <span :class="['text-5xl font-extrabold leading-none md:text-[56px]', getTone(result.tone).text]">
        {{ result.verdict }}
      </span>
      <span class="pb-1 text-sm font-medium text-white/90">{{ result.label }}</span>
    </div>

    <div class="mt-6 flex items-center justify-between text-xs text-muted">
      <span>Confidence</span>
      <span class="font-semibold text-white">{{ result.confidence }}%</span>
    </div>
    <ConfidenceBar :value="result.confidence" :tone="result.tone" class="mt-3" />
  </article>
</template>
