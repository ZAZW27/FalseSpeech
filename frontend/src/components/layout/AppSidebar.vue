<script setup>
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { brand } from '@/assets/data/site'
import { appLinks } from '@/assets/data/appNavigation'
import { capitalize, formatDuration, getInitials, toPercent } from '@/assets/js/format'
import Icon from '@/components/ui/icons/Icon.vue'
import PlanTag from '@/components/ui/badges/PlanTag.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'

const ANDROID_APK_URL = import.meta.env.VITE_ANDROID_APK_URL || '/downloads/FalseSpeech.apk'
const ANDROID_DEEP_LINK = 'falsespeech://open'
const ANDROID_TIERS = new Set(['pro_max', 'lifetime'])

const props = defineProps({
  // { name, tier, quota_used, quota_limit } from GET /api/users/me. Null while loading.
  user: { type: Object, default: null },
})

// "navigate" lets the mobile drawer close itself after a link is clicked.
const emit = defineEmits(['navigate', 'logout'])
const router = useRouter()

const logoutMenuOpen = ref(false)
const canUseAndroidApp = computed(() => ANDROID_TIERS.has(String(props.user?.tier ?? '').toLowerCase()))
const isAndroidDevice = () =>
  typeof navigator !== 'undefined' && /android/i.test(navigator.userAgent || '')

const handleAndroidAppClick = () => {
  emit('navigate')
  if (!canUseAndroidApp.value) {
    router.push('/plan')
    return
  }

  // On Android browser: try opening the installed app via deep link first.
  // If the app is not installed (tab stays visible), fall back to direct APK download.
  if (isAndroidDevice()) {
    let appOpened = false
    const onVisibility = () => {
      if (document.hidden) appOpened = true
    }
    document.addEventListener('visibilitychange', onVisibility, { once: true })
    window.location.href = ANDROID_DEEP_LINK
    setTimeout(() => {
      document.removeEventListener('visibilitychange', onVisibility)
      if (!appOpened && !document.hidden) {
        window.location.href = ANDROID_APK_URL
      }
    }, 1200)
    return
  }

  // Desktop browser: direct APK download
  const link = document.createElement('a')
  link.href = ANDROID_APK_URL
  link.download = 'FalseSpeech.apk'
  link.rel = 'noopener noreferrer'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

const toggleLogoutMenu = () => {
  logoutMenuOpen.value = !logoutMenuOpen.value
}

const confirmLogout = () => {
  logoutMenuOpen.value = false
  emit('logout')
}

const TIER_LABELS = { free: 'Free', pro: 'Pro', pro_max: 'Pro Max', lifetime: 'Lifetime' }
const planLabel = computed(() => {
  const raw = String(props.user?.tier ?? '')
  const formatted = TIER_LABELS[raw] ?? capitalize(raw.replace(/_/g, ' '))
  return `${formatted} plan`
})
const balanceLabel = computed(
  () => `Rp${new Intl.NumberFormat('id-ID').format(Number(props.user?.balance) || 0)}`,
)
const usedLabel = computed(() => formatDuration(props.user?.quota_used))
const limitLabel = computed(() => formatDuration(props.user?.quota_limit))
const percent = computed(() => toPercent(props.user?.quota_used, props.user?.quota_limit))
</script>

<template>
  <div class="flex h-full flex-col px-5 py-8">
    <RouterLink to="/" class="flex items-center gap-2.5 px-2 text-xl font-bold text-white" @click="$emit('navigate')">
      <Icon name="logo" :size="32" />
      {{ brand.name }}
    </RouterLink>

    <nav class="mt-8 flex flex-col gap-1.5" aria-label="App navigation">
      <RouterLink
        v-for="link in appLinks"
        :key="link.to"
        :to="link.to"
        class="flex h-12 items-center gap-3 rounded-xl border border-transparent px-4 text-[15px] font-medium text-secondary/70 transition hover:bg-white/5 hover:text-white"
        active-class="!border-brand-green/40 !bg-white/5 !text-white"
        @click="$emit('navigate')"
      >
        <Icon :name="link.icon" :size="20" />
        {{ link.label }}
      </RouterLink>
    </nav>

    <div class="mt-auto flex flex-col gap-5 pt-8">
      <!-- Android App Download / Open App button (Pro, Pro Max, Lifetime) -->
      <button
        type="button"
        class="flex items-center justify-between gap-2 rounded-xl border border-brand-green/30 bg-brand-green/10 px-3.5 py-2.5 text-left text-xs font-semibold text-white transition hover:border-brand-green/60 hover:bg-brand-green/20"
        @click="handleAndroidAppClick"
      >
        <span class="flex items-center gap-2.5">
          <Icon name="mobile" :size="16" class="text-brand-green" />
          <span>{{ canUseAndroidApp ? 'Download Android App' : 'Android App (Pro Max+)' }}</span>
        </span>
        <Icon name="download" :size="13" class="text-brand-green/80" />
      </button>

      <div v-if="user" class="rounded-2xl border border-back-secondary bg-back-secondary/40 p-5">
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-white">{{ planLabel }}</span>
          <PlanTag label="ACTIVE" />
        </div>
        <div class="mt-3 flex items-center justify-between border-b border-white/10 pb-3 text-xs">
          <span class="text-secondary/70">Balance</span>
          <span class="font-bold text-brand-green">{{ balanceLabel }}</span>
        </div>
        <div class="mt-3 flex items-center justify-between text-xs text-secondary/70">
          <span>Today</span>
          <span class="font-semibold text-white">{{ usedLabel }} / {{ limitLabel }}</span>
        </div>
        <ConfidenceBar :value="percent" tone="lime" class="mt-3" />
      </div>

      <div class="relative">
        <!-- Solid inline dropdown popover (replaces full-screen modal) -->
        <div
          v-if="logoutMenuOpen"
          role="menu"
          class="absolute bottom-full left-0 right-0 z-40 mb-2 rounded-xl border border-white/15 bg-[#0f172a] p-3 shadow-2xl"
        >
          <p class="text-xs font-semibold text-white">Log out of False Speech?</p>
          <p class="mt-0.5 text-[11px] text-slate-400">Your local session will be cleared.</p>
          <div class="mt-2.5 flex items-center justify-end gap-2">
            <button
              type="button"
              class="rounded-lg border border-white/15 bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-700"
              @click="logoutMenuOpen = false"
            >
              Cancel
            </button>
            <button
              type="button"
              class="rounded-lg bg-red-600 px-2.5 py-1.5 text-xs font-semibold text-white transition hover:bg-red-500"
              @click="confirmLogout"
            >
              Log out
            </button>
          </div>
        </div>

        <div v-if="user" class="flex items-center gap-3 px-1">
          <RouterLink
            to="/profile"
            class="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-back-secondary to-brand-green text-sm font-bold text-white"
            @click="$emit('navigate')"
          >
            {{ getInitials(user.name) }}
          </RouterLink>
          <div class="min-w-0">
            <RouterLink
              to="/profile"
              class="block truncate text-sm font-semibold text-white hover:text-brand-green"
              @click="$emit('navigate')"
            >
              {{ user.name }}
            </RouterLink>
            <button
              type="button"
              class="inline-flex items-center gap-1.5 text-xs text-secondary/70 transition hover:text-secondary"
              :aria-expanded="logoutMenuOpen"
              @click="toggleLogoutMenu"
            >
              <Icon name="logout" :size="12" />
              Log out
            </button>
          </div>
        </div>

        <button
          v-else
          type="button"
          class="flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-secondary/80 transition hover:bg-white/10 hover:text-white"
          :aria-expanded="logoutMenuOpen"
          @click="toggleLogoutMenu"
        >
          <Icon name="logout" :size="14" />
          Log out
        </button>
      </div>
    </div>
  </div>
</template>
