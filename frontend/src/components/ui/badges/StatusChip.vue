<script setup>
defineProps({
  label: { type: String, required: true },
  tone: { type: String, default: 'success', validator: (v) => ['danger', 'success', 'lime'].includes(v) },
})

const tones = {
  danger: 'border-danger/40 bg-danger/10 text-danger',
  success: 'border-brand-green/40 bg-brand-green/10 text-brand-green',
  lime: 'border-lime-400/40 bg-lime-400/10 text-lime-300',
}
</script>

<template>
  <span :class="['inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', tones[tone]]">
    <span class="size-1.5 rounded-full bg-current" />
    {{ label }}
  </span>
</template>
