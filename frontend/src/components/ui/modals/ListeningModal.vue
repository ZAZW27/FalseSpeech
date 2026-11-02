<script setup>
import { computed } from 'vue'
import { useListeningSession } from '@/assets/js/useListeningSession'
import BaseModal from '@/components/ui/modals/BaseModal.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import WaveformBars from '@/components/ui/charts/WaveformBars.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'
import { getTone } from '@/assets/js/tone'

const { isOpen, result, stop } = useListeningSession()

const visible = computed({
  get: () => isOpen.value,
  set: (value) => {
    if (!value) stop()
  },
})
</script>

<template>
  <BaseModal v-model="visible" label="Listening">
    <div class="p-8">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-lime-400">Listening...</p>

      <div class="mt-6 h-20">
        <WaveformBars :count="20" animated bar-width-class="w-2" />
      </div>

      <div class="mt-6 flex items-end gap-4">
        <span :class="['text-5xl font-extrabold leading-none', getTone(result.tone).text]">
          {{ result.verdict }}
        </span>
        <span class="pb-1 text-sm font-medium text-white/90">{{ result.label }}</span>
      </div>

      <div class="mt-6 flex items-center justify-between text-xs text-muted">
        <span>Confidence</span>
        <span class="font-semibold text-white">{{ result.confidence }}%</span>
      </div>
      <ConfidenceBar :value="result.confidence" :tone="result.tone" class="mt-3" />

      <BaseButton variant="outlineLight" block class="mt-8" @click="stop">Stop listening</BaseButton>
    </div>
  </BaseModal>
</template>
