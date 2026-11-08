<script setup>
import Icon from '@/components/ui/icons/Icon.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  sub: { type: String, default: '' },
  tone: { type: String, default: 'blue', validator: (v) => ['blue', 'cyan', 'danger', 'success'].includes(v) },
  // 0-100. When set, a progress bar is shown under the sub text.
  progress: { type: Number, default: null },
})

const tiles = {
  blue: 'bg-back-secondary text-secondary',
  cyan: 'bg-cyan-400/15 text-cyan-300',
  danger: 'bg-red-400/15 text-red-400',
  success: 'bg-brand-green/15 text-brand-green',
}
const values = {
  blue: 'text-white',
  cyan: 'text-white',
  danger: 'text-red-400',
  success: 'text-brand-green',
}
</script>

<template>
  <article class="flex flex-col rounded-3xl border border-back-secondary bg-back-secondary/40 p-5 sm:p-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <span :class="['flex size-[38px] shrink-0 items-center justify-center rounded-xl', tiles[tone]]">
        <Icon :name="icon" :size="18" />
      </span>
      <p class="text-sm text-secondary/70">{{ label }}</p>
    </div>

    <p :class="['mt-5 text-3xl font-extrabold leading-none sm:text-[36px]', values[tone]]">{{ value }}</p>

    <p v-if="sub" class="mt-4 text-xs text-secondary/70">{{ sub }}</p>
    <ConfidenceBar v-if="progress !== null" :value="progress" tone="lime" class="mt-3" />
  </article>
</template>
