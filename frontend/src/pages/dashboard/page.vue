<script setup>
// Temporary test page. Replaced by the real dashboard in the next step.
import AppLayout from '@/components/layout/AppLayout.vue'
</script>

<template>
  <AppLayout>
    <template #default="{ user }">
      <h1 class="text-3xl font-extrabold">Dashboard Test</h1>
      <p class="mt-2 text-sm text-muted">Signed in as {{ user.name }} ({{ user.tier }})</p>
    </template>
  </AppLayout>
</template>
