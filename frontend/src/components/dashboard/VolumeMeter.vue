<script setup>
import { computed } from 'vue'

// Horizontal volume bar. Gray when silent, green when audio is detected.
const props = defineProps({
  volume: { type: Number, default: 0 }, // 0 to 100
  silentBelow: { type: Number, default: 5 },
})

const silent = computed(() => props.volume < props.silentBelow)
</script>

<template>
  <div
    class="h-3 overflow-hidden rounded-full border border-white/10 bg-white/10"
    role="meter"
    aria-label="Audio volume"
    :aria-valuenow="Math.round(volume)"
    aria-valuemin="0"
    aria-valuemax="100"
  >
    <div
      :class="['h-full rounded-full transition-[width] duration-75 ease-out', silent ? 'bg-slate-600' : 'bg-brand-green']"
      :style="{ width: `${volume}%` }"
    />
  </div>
</template>
