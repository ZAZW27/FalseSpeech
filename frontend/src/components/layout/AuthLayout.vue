<script setup>
// Split screen for authentication pages.
// Left: brand panel (slot "brand"), hidden below lg. Right: the form (default slot).
</script>

<template>
  <div class="grid min-h-screen bg-white lg:grid-cols-2">
    <aside class="relative hidden overflow-hidden bg-gradient-to-br from-back-secondary via-back-prime to-back-prime lg:block">
      <slot name="brand" />
    </aside>

    <section class="flex items-center justify-center px-5 py-10 sm:px-8 lg:px-12">
      <div class="w-full max-w-[480px]">
        <slot />
      </div>
    </section>
  </div>
</template>
