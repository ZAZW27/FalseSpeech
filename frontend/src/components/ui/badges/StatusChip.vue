<script setup>
defineProps({
  label: { type: String, required: true },
  tone: { type: String, default: 'success', validator: (v) => ['danger', 'success', 'lime'].includes(v) },
})

const dotColors = {
  danger: 'bg-red-400',
  success: 'bg-brand-green',
  lime: 'bg-brand-green',
}
</script>

<template>
  <span
    class="inline-flex items-center gap-2 rounded-full border-2 border-white/30 bg-transparent px-3 py-1 text-xs font-semibold text-slate-100"
  >
    <span :class="['size-1.5 rounded-full', dotColors[tone]]" />
    {{ label }}
  </span>
</template>
