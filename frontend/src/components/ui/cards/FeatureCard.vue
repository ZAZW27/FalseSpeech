<script setup>
defineProps({
  number: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, required: true },
})
</script>

<template>
  <article
    class="rounded-3xl border border-white/10 bg-white/[0.04] p-8 backdrop-blur transition hover:border-lime-400/30"
  >
    <span
      class="flex size-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-green to-[#1b8fd1] text-sm font-bold text-white"
    >
      {{ number }}
    </span>
    <h3 class="mt-8 text-2xl font-bold">{{ title }}</h3>
    <p class="mt-5 text-[15px] leading-relaxed text-muted">{{ description }}</p>
  </article>
</template>
