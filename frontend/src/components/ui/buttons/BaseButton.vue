<script setup>
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  variant: {
    type: String,
    default: 'primary',
    validator: (v) => ['primary', 'dark', 'outline', 'outlineLight', 'ghost'].includes(v),
  },
  size: { type: String, default: 'md', validator: (v) => ['sm', 'md', 'lg'].includes(v) },
  to: { type: [String, Object], default: null },
  href: { type: String, default: null },
  type: { type: String, default: 'button' },
  block: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
})

const tag = computed(() => {
  if (props.to) return RouterLink
  if (props.href) return 'a'
  return 'button'
})

const variants = {
  primary:
    'bg-gradient-to-r from-lime-300 to-lime-400 text-navy-900 hover:brightness-105 shadow-[0_8px_24px_rgba(182,242,60,0.25)]',
  dark: 'bg-navy-900 text-white hover:bg-navy-800',
  outline: 'border border-navy-900 text-navy-900 hover:bg-navy-900/5',
  outlineLight: 'border border-white/25 text-white hover:bg-white/10',
  ghost: 'text-muted hover:text-white',
}

const sizes = {
  sm: 'h-10 px-5 text-sm',
  md: 'h-12 px-6 text-sm',
  lg: 'h-[50px] px-8 text-[15px]',
}
</script>

<template>
  <component
    :is="tag"
    :to="to"
    :href="href"
    :type="tag === 'button' ? type : undefined"
    :disabled="tag === 'button' ? disabled : undefined"
    :class="[
      'inline-flex items-center justify-center gap-2 rounded-full font-semibold transition disabled:cursor-not-allowed disabled:opacity-50',
      variants[variant],
      sizes[size],
      block ? 'w-full' : '',
    ]"
  >
    <slot />
  </component>
</template>
