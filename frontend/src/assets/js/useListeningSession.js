import { computed, ref } from 'vue'
import { heroResults } from '@/assets/data/heroResults'

const ROTATE_MS = 4000

// Module-level state so any component can open the same listening session.
const isOpen = ref(false)
const index = ref(0)
let timer = null

export function useListeningSession() {
  const result = computed(() => heroResults[index.value])

  // Simulated cycle. Replace with the real streaming API when the backend exists.
  const start = () => {
    index.value = 0
    isOpen.value = true
    clearInterval(timer)
    timer = setInterval(() => {
      index.value = (index.value + 1) % heroResults.length
    }, ROTATE_MS)
  }

  const stop = () => {
    isOpen.value = false
    clearInterval(timer)
    timer = null
  }

  return { isOpen, result, start, stop }
}
