<script setup>
import { nextTick, ref, watch } from 'vue'

// logs: [{ id, time, text, tone: 'fake' | 'real' | 'muted' }]
const props = defineProps({
  logs: { type: Array, default: () => [] },
  listening: { type: Boolean, default: false },
})

const scroller = ref(null)

// Keep the newest line in view, like a terminal.
watch(
  () => props.logs.length,
  async () => {
    await nextTick()
    if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
  },
)

const toneClass = {
  fake: 'text-danger',
  real: 'text-brand-green',
  muted: 'text-slate-400',
}
</script>

<template>
  <section class="flex flex-col overflow-hidden rounded-3xl border border-white/10 bg-black">
    <header class="flex items-center justify-between border-b border-white/10 px-5 py-3">
      <h2 class="font-mono text-xs uppercase tracking-[0.2em] text-slate-400">Live log</h2>
      <span class="flex items-center gap-2 font-mono text-xs text-slate-400">
        <span :class="['size-2 rounded-full', listening ? 'animate-pulse bg-brand-green' : 'bg-slate-600']" />
        {{ listening ? 'live' : 'idle' }}
      </span>
    </header>

    <div
      ref="scroller"
      class="h-[240px] overflow-y-auto px-5 py-4 font-mono text-xs leading-6 xl:h-[280px]"
      role="log"
      aria-live="off"
      tabindex="0"
    >
      <p v-if="!logs.length" class="text-slate-500">Waiting for audio. Press start to begin.</p>

      <p v-for="log in logs" :key="log.id" class="whitespace-pre-wrap break-words">
        <span class="text-slate-600">[{{ log.time }}]</span>
        <span :class="toneClass[log.tone] ?? toneClass.muted"> {{ log.text }}</span>
      </p>
    </div>
  </section>
</template>
