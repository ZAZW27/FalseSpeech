<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useBodyScrollLock } from '@/assets/js/useBodyScrollLock'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  label: { type: String, default: 'Dialog' },
  maxWidthClass: { type: String, default: 'md:max-w-[480px]' },
})

const emit = defineEmits(['update:modelValue'])

const close = () => emit('update:modelValue', false)

const onKeydown = (event) => {
  if (event.key === 'Escape' && props.modelValue) close()
}

useBodyScrollLock(() => props.modelValue)

onMounted(() => window.addEventListener('keydown', onKeydown))
onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-[60] flex items-end justify-center md:items-center md:p-6"
      role="dialog"
      aria-modal="true"
      :aria-label="label"
    >
      <div class="absolute inset-0 animate-fade-in bg-navy-950/80 backdrop-blur-sm" @click="close" />
      <div
        :class="[
          'relative w-full animate-sheet-up rounded-t-3xl border border-white/10 bg-navy-900 shadow-[0_30px_80px_rgba(0,0,0,0.5)] md:rounded-3xl',
          maxWidthClass,
        ]"
      >
        <slot />
      </div>
    </div>
  </Teleport>
</template>
