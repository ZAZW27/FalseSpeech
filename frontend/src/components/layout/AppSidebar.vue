<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { brand } from '@/assets/data/site'
import { appLinks } from '@/assets/data/appNavigation'
import { capitalize, formatDuration, getInitials, toPercent } from '@/assets/js/format'
import Icon from '@/components/ui/icons/Icon.vue'
import PlanTag from '@/components/ui/badges/PlanTag.vue'
import ConfidenceBar from '@/components/ui/charts/ConfidenceBar.vue'

const props = defineProps({
  // { name, tier, quota_used, quota_limit } from GET /api/users/me. Null while loading.
  user: { type: Object, default: null },
})

// "navigate" lets the mobile drawer close itself after a link is clicked.
defineEmits(['navigate', 'logout'])

const planLabel = computed(() => `${capitalize(props.user?.tier ?? '')} plan`)
const usedLabel = computed(() => formatDuration(props.user?.quota_used))
const limitLabel = computed(() => formatDuration(props.user?.quota_limit))
const percent = computed(() => toPercent(props.user?.quota_used, props.user?.quota_limit))
</script>

<template>
  <div class="flex h-full flex-col px-5 py-8">
    <RouterLink to="/" class="flex items-center gap-2.5 px-2 text-xl font-bold text-white" @click="$emit('navigate')">
      <Icon name="waveform" :size="32" />
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

    <div v-if="user" class="mt-auto flex flex-col gap-6 pt-8">
      <div class="rounded-2xl border border-back-secondary bg-back-secondary/40 p-5">
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-white">{{ planLabel }}</span>
          <PlanTag label="ACTIVE" />
        </div>
        <div class="mt-4 flex items-center justify-between text-xs text-secondary/70">
          <span>Today</span>
          <span class="font-semibold text-white">{{ usedLabel }} / {{ limitLabel }}</span>
        </div>
        <ConfidenceBar :value="percent" tone="lime" class="mt-3" />
      </div>

      <div class="flex items-center gap-3 px-1">
        <span
          class="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-back-secondary to-brand-green text-sm font-bold text-white"
          aria-hidden="true"
        >
          {{ getInitials(user.name) }}
        </span>
        <div class="min-w-0">
          <p class="truncate text-sm font-semibold text-white">{{ user.name }}</p>
          <button
            type="button"
            class="text-xs text-secondary/70 transition hover:text-secondary"
            @click="$emit('logout')"
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
