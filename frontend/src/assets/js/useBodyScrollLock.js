import { watch, onUnmounted, toValue } from 'vue'

export function useBodyScrollLock(isLocked) {
  const apply = (locked) => {
    document.body.style.overflow = locked ? 'hidden' : ''
  }

  watch(() => toValue(isLocked), apply, { immediate: true })

  onUnmounted(() => apply(false))
}
