<script setup>
import { computed } from 'vue'

// result: { label, tone: 'real' | 'fake' | 'uncertain', fake, real } or null
const props = defineProps({
  result: { type: Object, default: null },
  listening: { type: Boolean, default: false },
  statusText: { type: String, default: '' },
  statusWarn: { type: Boolean, default: false },
  size: { type: String, default: 'md', validator: (v) => ['md', 'xl'].includes(v) },
})

const toneClass = {
  real: 'text-brand-green',
  fake: 'text-red-400',
  uncertain: 'text-secondary',
}

const label = computed(() => props.result?.label ?? (props.listening ? '...' : '-'))
const colorClass = computed(() => (props.result ? toneClass[props.result.tone] : 'text-secondary/60'))

const probs = computed(() => {
  if (props.result) {
    return `fake ${(props.result.fake * 100).toFixed(1)}% / real ${(props.result.real * 100).toFixed(1)}%`
  }
  return props.listening ? 'capturing' : 'Waiting for audio...'
})
</script>

<template>
  <div class="text-center" aria-live="polite">
    <p :class="['font-extrabold tracking-wide', colorClass, size === 'xl' ? 'text-5xl sm:text-6xl' : 'text-4xl sm:text-5xl']">
      {{ label }}
    </p>
    <p class="mt-3 text-sm text-secondary/70">{{ probs }}</p>
    <p
      v-if="statusText"
      :class="['mt-2 font-mono text-xs', statusWarn ? 'font-semibold text-secondary' : 'text-secondary/60']"
    >
      {{ statusText }}
    </p>
  </div>
</template>
