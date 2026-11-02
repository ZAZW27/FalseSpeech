<script setup>
import { RouterLink } from 'vue-router'
import { navLinks } from '@/assets/data/navigation'
import { useBodyScrollLock } from '@/assets/js/useBodyScrollLock'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import IconButton from '@/components/ui/buttons/IconButton.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
})

const emit = defineEmits(['update:modelValue'])

const close = () => emit('update:modelValue', false)

useBodyScrollLock(() => props.modelValue)
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
      <div class="absolute inset-0 animate-fade-in bg-navy-950/70 backdrop-blur-sm" @click="close" />

      <aside
        class="absolute inset-y-0 right-0 flex w-[300px] max-w-[85vw] animate-fade-in flex-col bg-navy-900 px-6 pb-6 pt-5 shadow-[-20px_0_60px_rgba(0,0,0,0.5)]"
      >
        <div class="flex items-center justify-between">
          <span class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Menu</span>
          <IconButton icon="close" label="Close menu" @click="close" />
        </div>

        <ul class="mt-6 flex flex-col">
          <li v-for="link in navLinks" :key="link.to" class="border-b border-white/10">
            <RouterLink :to="link.to" class="block py-4 text-3xl font-bold text-white" @click="close">
              {{ link.label }}
            </RouterLink>
          </li>
        </ul>

        <div class="mt-auto">
          <BaseButton to="/contact" block @click="close">Contact us</BaseButton>
        </div>
      </aside>
    </div>
  </Teleport>
</template>
