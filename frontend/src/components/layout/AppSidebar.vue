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

    <div class="mt-auto flex flex-col gap-6 pt-8">
      <div v-if="user" class="rounded-2xl border border-back-secondary bg-back-secondary/40 p-5">
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
            @click="$emit('logout')"
          >
            <Icon name="logout" :size="12" />
            Log out
          </button>
        </div>
      </div>

      <button
        v-else
        type="button"
        class="flex h-11 items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-secondary/80 transition hover:bg-white/10 hover:text-white"
        @click="$emit('logout')"
      >
        <Icon name="logout" :size="14" />
        Log out
      </button>
    </div>
  </div>
</template>
