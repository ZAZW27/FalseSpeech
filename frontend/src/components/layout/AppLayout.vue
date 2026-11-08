<script setup>
import { onMounted, provide, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { brand } from '@/assets/data/site'
import { authFetch, clearToken, getToken } from '@/assets/js/api'
import { useBodyScrollLock } from '@/assets/js/useBodyScrollLock'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import IconButton from '@/components/ui/buttons/IconButton.vue'
import Icon from '@/components/ui/icons/Icon.vue'

// Default topbar text. Pages can replace it with the "topbar" slot.
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
})

const router = useRouter()

// GET /api/users/me -> { name, tier, quota_used, quota_limit }
const user = ref(null)
const isLoading = ref(true)
const errorMessage = ref('')
const drawerOpen = ref(false)

const logout = () => {
  clearToken()
  router.replace('/login')
}

const loadUser = async () => {
  if (!getToken()) {
    router.replace('/login')
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    const response = await authFetch('/api/users/me')

    if (response.status === 401) {
      // Expired or invalid token.
      logout()
      return
    }
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)

    user.value = await response.json()
  } catch {
    errorMessage.value = 'We could not load your account. Please check your connection and try again.'
  } finally {
    isLoading.value = false
  }
}

// Called by pages when the live stream reports new quota numbers.
const updateQuota = (used, limit) => {
  if (!user.value) return
  user.value.quota_used = used
  if (limit != null) user.value.quota_limit = limit
}

// Child components can inject these instead of using the slot props.
provide('appUser', user)
provide('updateQuota', updateQuota)

useBodyScrollLock(drawerOpen)
onMounted(loadUser)
</script>

<template>
  <div class="min-h-screen bg-back-prime text-white lg:pl-[260px]">
    <!-- Desktop sidebar -->
    <aside class="fixed inset-y-0 left-0 z-30 hidden w-[260px] border-r border-back-secondary bg-back-prime lg:block">
      <AppSidebar :user="user" @logout="logout" />
    </aside>

    <!-- Mobile navbar -->
    <header
      class="sticky top-0 z-30 flex h-[72px] items-center justify-between border-b border-back-secondary bg-back-prime/90 px-5 backdrop-blur lg:hidden"
    >
      <RouterLink to="/" class="flex items-center gap-2.5 text-lg font-bold">
        <Icon name="waveform" :size="28" />
        {{ brand.name }}
      </RouterLink>
      <IconButton icon="menu" label="Open menu" @click="drawerOpen = true" />
    </header>

    <!-- Mobile drawer -->
    <Teleport to="body">
      <div v-if="drawerOpen" class="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menu">
        <div class="absolute inset-0 animate-fade-in bg-back-prime/70 backdrop-blur-sm" @click="drawerOpen = false" />
        <aside
          class="absolute inset-y-0 left-0 w-[280px] max-w-[85vw] animate-fade-in border-r border-back-secondary bg-back-prime shadow-[20px_0_60px_rgba(0,0,0,0.5)]"
        >
          <AppSidebar :user="user" @navigate="drawerOpen = false" @logout="logout" />
        </aside>
      </div>
    </Teleport>

    <main class="mx-auto w-full max-w-[1180px] px-5 pb-12 pt-6 lg:px-10 lg:pt-9">
      <!-- Loaded -->
      <template v-if="user">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <slot name="topbar" :user="user">
              <h1 class="text-3xl font-extrabold tracking-tight lg:text-[32px]">{{ title }}</h1>
              <p v-if="subtitle" class="mt-1.5 text-sm text-secondary/70">{{ subtitle }}</p>
            </slot>
          </div>
          <slot name="actions" :user="user" />
        </div>

        <div class="mt-8">
          <slot :user="user" :update-quota="updateQuota" :refresh="loadUser" />
        </div>
      </template>

      <!-- Error -->
      <div v-else-if="errorMessage" class="mx-auto mt-24 max-w-[420px] text-center" role="alert">
        <p class="text-secondary/70">{{ errorMessage }}</p>
        <BaseButton class="mt-6" @click="loadUser">Try again</BaseButton>
      </div>

      <!-- Loading -->
      <p v-else-if="isLoading" class="mt-24 text-center text-sm text-secondary/70" role="status">
        Loading your account...
      </p>
    </main>
  </div>
</template>
