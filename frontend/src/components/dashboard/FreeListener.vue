<script setup>
import { computed } from 'vue'
import { useAudioCapture } from '@/assets/js/useAudioCapture'
import PlayButton from '@/components/ui/buttons/PlayButton.vue'

// Scenario A: free users only see the play button and the verdict.
const props = defineProps({
  user: { type: Object, required: true },
  updateQuota: { type: Function, required: true },
})

const { status, isListening, verdict, errorMessage, start, stop } = useAudioCapture()

const toggle = () => (isListening.value ? stop() : start({ onQuota: props.updateQuota }))

const verdictClass = {
  REAL: 'text-brand-green drop-shadow-[0_0_24px_rgba(22,199,132,0.5)]',
  FAKE: 'text-danger drop-shadow-[0_0_24px_rgba(255,92,122,0.5)]',
  UNCERTAIN: 'text-lime-300 drop-shadow-[0_0_24px_rgba(212,255,107,0.4)]',
}

const hint = computed(() => {
  if (status.value === 'connecting') return 'Connecting...'
  if (isListening.value) return 'Listening...'
  return 'Tap to start listening'
})
</script>

<template>
  <div class="flex min-h-[60vh] flex-col items-center justify-center gap-10 py-6 text-center">
    <PlayButton
      size="xl"
      :playing="isListening"
      :pulse="isListening"
      :label="isListening ? 'Stop listening' : 'Start listening'"
      @click="toggle"
    />

    <div class="min-h-[96px]" aria-live="polite">
      <p v-if="verdict" :class="['text-5xl font-extrabold tracking-wide sm:text-6xl', verdictClass[verdict]]">
        {{ verdict }}
      </p>
      <p v-else class="text-base text-muted">{{ hint }}</p>
    </div>

    <p
      v-if="errorMessage"
      class="max-w-[420px] rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
      role="alert"
    >
      {{ errorMessage }}
    </p>
  </div>
</template>
