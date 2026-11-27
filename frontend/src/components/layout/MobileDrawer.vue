<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { navLinks } from '@/assets/data/navigation'
import { clearToken, getToken } from '@/assets/js/api'
import { useBodyScrollLock } from '@/assets/js/useBodyScrollLock'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import Icon from '@/components/ui/icons/Icon.vue'
import LogoutConfirmPopover from '@/components/ui/modals/LogoutConfirmPopover.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
})

const emit = defineEmits(['update:modelValue'])

const route = useRoute()
const router = useRouter()
const logoutConfirmOpen = ref(false)

const isLoggedIn = computed(() => {
  void route.fullPath
  void props.modelValue
  return Boolean(getToken())
})

const close = () => {
  logoutConfirmOpen.value = false
  emit('update:modelValue', false)
}

const confirmLogout = () => {
  clearToken()
  close()
  router.replace('/login')
}

watch(
  () => props.modelValue,
  (open) => {
    if (!open) logoutConfirmOpen.value = false
  },
)

useBodyScrollLock(() => props.modelValue)

// Auto-close mobile drawer when viewport widens to desktop (lg >= 1024px) so body scroll lock is never stuck
let desktopMq = null
const onViewportChange = (e) => {
  if (e.matches && props.modelValue) close()
}

onMounted(() => {
  if (typeof window !== 'undefined' && window.matchMedia) {
    desktopMq = window.matchMedia('(min-width: 1024px)')
    desktopMq.addEventListener?.('change', onViewportChange)
  }
})

onBeforeUnmount(() => {
  desktopMq?.removeEventListener?.('change', onViewportChange)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="drawer-slide" :duration="320">
      <div v-if="modelValue" class="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
        <div class="drawer-backdrop absolute inset-0 bg-black/65 backdrop-blur-sm" @click="close" />

        <aside
          class="drawer-panel absolute inset-y-0 right-0 flex w-[290px] max-w-[85vw] flex-col border-l-2 border-back-secondary bg-gradient-to-b from-back-prime via-back-prime to-back-secondary px-6 pb-6 pt-5 shadow-[-20px_0_60px_rgba(0,0,0,0.55)]"
        >
          <div class="flex items-center justify-between border-b border-white/10 pb-4">
            <span class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Menu</span>
            <button
              type="button"
              class="flex size-9 cursor-pointer items-center justify-center rounded-full border border-white/15 bg-white/5 text-lg leading-none text-slate-200 transition hover:bg-white/15 hover:text-white"
              aria-label="Close menu"
              @click="close"
            >
              &times;
            </button>
          </div>

          <ul class="mt-4 flex flex-col">
            <li v-for="link in navLinks" :key="link.to" class="border-b border-white/10 last:border-b-0">
              <RouterLink
                :to="link.to"
                class="block py-3.5 text-base font-semibold text-slate-100 transition hover:text-brand-green"
                exact-active-class="!text-brand-green"
                @click="close"
              >
                {{ link.label }}
              </RouterLink>
            </li>
          </ul>

          <div class="relative mt-auto flex flex-col gap-2.5 border-t border-white/10 pt-5">
            <template v-if="isLoggedIn">
              <LogoutConfirmPopover
                :open="logoutConfirmOpen"
                position-class="bottom-full left-0 right-0 mb-2"
                @cancel="logoutConfirmOpen = false"
                @confirm="confirmLogout"
              />
              <BaseButton to="/dashboard" size="sm" block @click="close">
                <Icon name="dashboard" :size="15" />
                Dashboard
              </BaseButton>
              <BaseButton
                size="sm"
                variant="outlineLight"
                block
                :aria-expanded="logoutConfirmOpen"
                @click="logoutConfirmOpen = !logoutConfirmOpen"
              >
                <Icon name="logout" :size="14" />
                Log out
              </BaseButton>
            </template>
            <template v-else>
              <BaseButton to="/register" size="sm" block @click="close">
                Sign up
              </BaseButton>
              <BaseButton to="/login" size="sm" variant="outlineLight" block @click="close">
                Sign in
              </BaseButton>
            </template>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
