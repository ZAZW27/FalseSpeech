<script setup>
</script>

<template>
  <div class="grid min-h-screen bg-surface-light lg:grid-cols-2">
    <aside class="relative hidden overflow-hidden bg-gradient-to-br from-navy-800 via-navy-900 to-navy-950 lg:block">
      <slot name="brand" />
    </aside>

    <section class="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
      <div class="w-full max-w-[480px]">
        <slot />
      </div>
    </section>
  </div>
</template>
