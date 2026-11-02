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
  blue: 'bg-[#1b5bff]/20 text-[#5b9bff]',
  cyan: 'bg-cyan-400/15 text-cyan-300',
  danger: 'bg-danger/15 text-danger',
  success: 'bg-brand-green/15 text-brand-green',
}
const values = {
  blue: 'text-white',
  cyan: 'text-white',
  danger: 'text-danger',
  success: 'text-brand-green',
}
</script>

<template>
  <article class="flex flex-col rounded-3xl border border-white/10 bg-white/[0.04] p-5 sm:p-6">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center">
      <span :class="['flex size-[38px] shrink-0 items-center justify-center rounded-xl', tiles[tone]]">
        <Icon :name="icon" :size="18" />
      </span>
      <p class="text-sm text-muted">{{ label }}</p>
    </div>

    <p :class="['mt-5 text-3xl font-extrabold leading-none sm:text-[36px]', values[tone]]">{{ value }}</p>

    <p v-if="sub" class="mt-4 text-xs text-muted">{{ sub }}</p>
    <ConfidenceBar v-if="progress !== null" :value="progress" tone="lime" class="mt-3" />
  </article>
</template>
