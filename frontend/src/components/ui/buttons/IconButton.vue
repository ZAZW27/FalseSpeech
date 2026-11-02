<script setup>
import Icon from '@/components/ui/icons/Icon.vue'

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  size: { type: Number, default: 42 },
  iconSize: { type: Number, default: 20 },
})

defineEmits(['click'])
</script>

<template>
  <button
    type="button"
    :aria-label="label"
    :style="{ width: `${size}px`, height: `${size}px` }"
    class="inline-flex items-center justify-center rounded-full border border-white/15 text-white transition hover:bg-white/10"
    @click="$emit('click', $event)"
  >
    <Icon :name="icon" :size="iconSize" />
  </button>
</template>
