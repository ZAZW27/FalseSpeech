<script setup>
defineProps({
  label: { type: String, required: true },
  tone: { type: String, default: 'success', validator: (v) => ['danger', 'success', 'lime'].includes(v) },
})

const tones = {
  danger: 'border-red-400/40 bg-red-400/10 text-red-400',
  success: 'border-brand-green/40 bg-brand-green/10 text-brand-green',
  lime: 'border-brand-green/40 bg-brand-green/10 text-secondary',
}
</script>

<template>
  <span :class="['inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold', tones[tone]]">
    <span class="size-1.5 rounded-full bg-current" />
    {{ label }}
  </span>
</template>
