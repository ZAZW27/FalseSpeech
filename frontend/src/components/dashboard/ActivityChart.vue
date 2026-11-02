<script setup>
import { computed } from 'vue'
import { buildWeekly } from '@/assets/js/historyStats'

const props = defineProps({
  history: { type: Array, default: () => [] },
})

const BAR_MAX_PX = 140

const days = computed(() => {
  const week = buildWeekly(props.history)
  const max = Math.max(1, ...week.map((day) => day.count))
  return week.map((day) => ({
    ...day,
    height: day.count === 0 ? 6 : Math.max(10, Math.round((day.count / max) * BAR_MAX_PX)),
  }))
})
</script>

<template>
  <section class="rounded-3xl border border-white/10 bg-white/[0.04] p-6">
    <header class="flex items-start justify-between gap-3">
      <div>
        <h2 class="text-lg font-bold">Weekly activity</h2>
        <p class="mt-1 text-xs text-muted">Voice checks per day</p>
      </div>
      <span class="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/90">
        Last 7 days
      </span>
    </header>

    <div class="mt-8 flex items-end justify-between gap-2">
      <div v-for="day in days" :key="day.key" class="flex min-w-0 flex-1 flex-col items-center gap-2">
        <span :class="['text-xs tabular-nums', day.isToday ? 'font-semibold text-lime-300' : 'text-muted']">
          {{ day.count }}
        </span>
        <div
          :class="[
            'w-full max-w-[34px] rounded-t-lg rounded-b-md transition-all duration-500',
            day.isToday
              ? 'bg-gradient-to-t from-brand-green to-lime-300'
              : 'bg-gradient-to-t from-[#1e3a8a] to-[#3b82f6]',
            day.count === 0 ? 'opacity-40' : '',
          ]"
          :style="{ height: `${day.height}px` }"
        />
        <span :class="['text-xs', day.isToday ? 'font-semibold text-white' : 'text-muted']">{{ day.label }}</span>
      </div>
    </div>
  </section>
</template>
