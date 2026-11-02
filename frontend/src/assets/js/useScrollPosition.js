import { onMounted, onUnmounted, ref, computed } from 'vue'

export function useScrollPosition(threshold = 24) {
  const scrollY = ref(0)
  const isScrolled = computed(() => scrollY.value > threshold)

  const update = () => {
    scrollY.value = window.scrollY
  }

  onMounted(() => {
    update()
    window.addEventListener('scroll', update, { passive: true })
  })

  onUnmounted(() => {
    window.removeEventListener('scroll', update)
  })

  return { scrollY, isScrolled }
}
