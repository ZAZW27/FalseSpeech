<script setup>
import { computed } from 'vue'
import { formatDuration, toPercent } from '@/assets/js/format'
import StatCard from '@/components/ui/cards/StatCard.vue'

// Everything here is derived from /api/users/me and /api/history.
const props = defineProps({
  usedSeconds: { type: Number, default: 0 },
  limitSeconds: { type: Number, default: 0 },
  total: { type: Number, default: 0 },
  ai: { type: Number, default: 0 },
  human: { type: Number, default: 0 },
})

const share = (count) => (props.total ? Math.round((count / props.total) * 100) : 0)

const cards = computed(() => {
  const used = toPercent(props.usedSeconds, props.limitSeconds)
  return [
    {
      id: 'listening',
      icon: 'history',
      tone: 'blue',
      label: 'Listening today',
      value: formatDuration(props.usedSeconds),
      sub: `of ${formatDuration(props.limitSeconds)} daily limit, ${used}% used`,
      progress: used,
    },
    {
      id: 'checks',
      icon: 'trend',
      tone: 'cyan',
      label: 'Total checks',
      value: props.total,
      sub: 'All recorded sessions',
      progress: null,
    },
    {
      id: 'ai',
      icon: 'alert',
      tone: 'danger',
      label: 'AI voices flagged',
      value: props.ai,
      sub: `${share(props.ai)}% of all checks`,
      progress: null,
    },
    {
      id: 'human',
      icon: 'user',
      tone: 'success',
      label: 'Human voices',
      value: props.human,
      sub: `${share(props.human)}% of all checks`,
      progress: null,
    },
  ]
})
</script>

<template>
  <div class="grid grid-cols-2 gap-4 xl:grid-cols-4 xl:gap-5">
    <StatCard
      v-for="card in cards"
      :key="card.id"
      :icon="card.icon"
      :tone="card.tone"
      :label="card.label"
      :value="card.value"
      :sub="card.sub"
      :progress="card.progress"
    />
  </div>
</template>
