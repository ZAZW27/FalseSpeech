<script setup>
const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  type: {
    type: String,
    default: 'text',
    validator: (v) => ['text', 'email', 'tel', 'password', 'textarea'].includes(v),
  },
  // dark: for navy backgrounds. light: for white or light-blue backgrounds.
  tone: { type: String, default: 'dark', validator: (v) => ['dark', 'light'].includes(v) },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  error: { type: String, default: '' },
})

const model = defineModel({ type: String, default: '' })

const tones = {
  dark: {
    label: 'text-white/90',
    field: 'bg-white/5 text-white placeholder:text-muted/60 focus:border-lime-400',
    border: 'border-white/15',
  },
  light: {
    label: 'text-navy-900',
    field: 'bg-white text-navy-900 placeholder:text-navy-900/40 focus:border-brand-green',
    border: 'border-navy-900/15',
  },
}

const fieldClass = () =>
  [
    'w-full rounded-2xl border px-5 text-[15px] transition focus:outline-none',
    tones[props.tone].field,
    props.error ? 'border-danger' : tones[props.tone].border,
  ].join(' ')
</script>

<template>
  <div class="flex flex-col gap-2">
    <div class="flex items-center justify-between gap-4">
      <label :for="id" :class="['text-sm font-medium', tones[tone].label]">{{ label }}</label>
      <!-- Optional content on the right of the label row, e.g. "Forgot password?" -->
      <slot name="label-extra" />
    </div>

    <textarea
      v-if="type === 'textarea'"
      :id="id"
      v-model="model"
      rows="5"
      :placeholder="placeholder"
      :aria-invalid="error ? 'true' : undefined"
      :class="[fieldClass(), 'resize-y py-4']"
    />
    <input
      v-else
      :id="id"
      v-model="model"
      :type="type"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :aria-invalid="error ? 'true' : undefined"
      :class="[fieldClass(), 'h-[54px]']"
    />

    <p v-if="error" class="text-xs text-danger">{{ error }}</p>
  </div>
</template>
