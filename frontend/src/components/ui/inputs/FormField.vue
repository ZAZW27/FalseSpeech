<script setup>
defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  type: { type: String, default: 'text', validator: (v) => ['text', 'email', 'textarea'].includes(v) },
  placeholder: { type: String, default: '' },
  autocomplete: { type: String, default: 'off' },
  error: { type: String, default: '' },
})

const model = defineModel({ type: String, default: '' })

const fieldClass =
  'w-full rounded-2xl border bg-white/5 px-5 text-[15px] text-white placeholder:text-muted/60 transition focus:border-lime-400 focus:outline-none'
</script>

<template>
  <div class="flex flex-col gap-2">
    <label :for="id" class="text-sm font-medium text-white/90">{{ label }}</label>

    <textarea
      v-if="type === 'textarea'"
      :id="id"
      v-model="model"
      rows="5"
      :placeholder="placeholder"
      :aria-invalid="error ? 'true' : undefined"
      :class="[fieldClass, 'resize-y py-4', error ? 'border-danger' : 'border-white/15']"
    />
    <input
      v-else
      :id="id"
      v-model="model"
      :type="type"
      :placeholder="placeholder"
      :autocomplete="autocomplete"
      :aria-invalid="error ? 'true' : undefined"
      :class="[fieldClass, 'h-[54px]', error ? 'border-danger' : 'border-white/15']"
    />

    <p v-if="error" class="text-xs text-danger">{{ error }}</p>
  </div>
</template>
