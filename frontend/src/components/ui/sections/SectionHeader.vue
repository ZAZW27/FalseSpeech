<script setup>
defineProps({
  eyebrow: { type: String, required: true },
  title: { type: String, required: true },
  description: { type: String, default: '' },
  align: { type: String, default: 'left', validator: (v) => ['left', 'center', 'split'].includes(v) },
  tone: { type: String, default: 'dark', validator: (v) => ['dark', 'light'].includes(v) },
})
</script>

<template>
  <header
    :class="[
      align === 'center' ? 'mx-auto max-w-[980px] text-center' : '',
      align === 'split' ? 'grid gap-6 lg:grid-cols-2 lg:items-end lg:gap-20' : '',
    ]"
  >
    <div>
      <p
        :class="[
          'text-xs font-semibold uppercase tracking-[0.2em]',
          tone === 'dark' ? 'text-lime-400' : 'text-brand-green',
        ]"
      >
        {{ eyebrow }}
      </p>
      <h2
        :class="[
          'mt-4 text-balance text-3xl font-extrabold leading-tight tracking-tight md:text-4xl xl:text-[44px]',
          tone === 'dark' ? 'text-white' : 'text-navy-900',
          align === 'split' ? 'max-w-[660px]' : '',
        ]"
      >
        {{ title }}
      </h2>
    </div>
    <p
      v-if="description"
      :class="[
        'text-base leading-relaxed',
        tone === 'dark' ? 'text-muted' : 'text-navy-900/70',
        align === 'center' ? 'mx-auto mt-5 max-w-[620px]' : '',
        align === 'left' ? 'mt-5 max-w-[620px]' : '',
        align === 'split' ? 'lg:max-w-[460px] lg:justify-self-end' : '',
      ]"
    >
      {{ description }}
    </p>
  </header>
</template>
