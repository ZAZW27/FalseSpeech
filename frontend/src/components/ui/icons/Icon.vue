<script setup>
// PLACEHOLDER ICON. Every <Icon name="..." /> in the project renders a visible "@".
// Find all usages with: grep -rn "<Icon" src
// Replace the template below with your real icon library when ready.
defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 20 },
})
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center font-bold leading-none"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.8)}px` }"
    :data-icon="name"
    :title="`icon: ${name}`"
    aria-hidden="true"
  >@</span>
</template>
