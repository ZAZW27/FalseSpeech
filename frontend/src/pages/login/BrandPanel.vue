<script setup>
import { RouterLink } from 'vue-router'
import { brand } from '@/assets/data/site'
import { heroResults } from '@/assets/data/heroResults'
import Icon from '@/components/ui/icons/Icon.vue'
import AnalysisCard from '@/components/ui/cards/AnalysisCard.vue'
import WaveformBars from '@/components/ui/charts/WaveformBars.vue'

const copy = {
  title: 'Welcome back.',
  subtitle: 'Log in to see your history, daily usage and plan. Your next check is one tap away.',
}

// The Figma brand panel shows the HUMAN result card.
const result = heroResults.find((item) => item.id === 'human')
</script>

<template>
  <div class="relative h-full min-h-screen">
    <!-- Background glows and ghost wordmark -->
    <span class="pointer-events-none absolute -left-48 -top-44 size-[520px] rounded-full bg-[#1b5bff]/50 blur-[110px]" />
    <span class="pointer-events-none absolute -bottom-28 -right-24 size-[480px] rounded-full bg-lime-400/40 blur-[120px]" />
    <span
      class="pointer-events-none absolute -left-2 top-[150px] select-none text-[200px] font-extrabold uppercase leading-[0.85] tracking-tighter text-white/[0.04]"
      aria-hidden="true"
    >
      False<br />Speech
    </span>

    <div class="relative flex h-full min-h-screen flex-col px-12 py-14 xl:px-[72px]">
      <RouterLink to="/" class="flex w-fit items-center gap-2.5 text-2xl font-bold text-white">
        <Icon name="waveform" :size="32" />
        {{ brand.name }}
      </RouterLink>

      <h2 class="mt-[90px] text-balance text-5xl font-extrabold leading-[1.05] tracking-tight xl:text-[64px]">
        {{ copy.title }}
      </h2>
      <p class="mt-8 max-w-[480px] text-lg leading-relaxed text-muted">{{ copy.subtitle }}</p>

      <div class="mt-12 w-[343px] max-w-full">
        <AnalysisCard :result="result" />
      </div>
    </div>

    <!-- Waveform bleeds off the right edge, as in Figma -->
    <div class="absolute bottom-20 left-12 h-[120px] w-[696px] xl:left-[72px] xl:h-[167px]">
      <WaveformBars
        :count="44"
        wobbles
        bar-width-class="w-2"
        bar-class="bg-gradient-to-b from-lime-300 to-brand-green"
      />
    </div>
  </div>
</template>
