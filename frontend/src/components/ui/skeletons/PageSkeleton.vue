<script setup>
defineProps({
  variant: {
    type: String,
    default: 'dashboard',
    validator: (v) => ['dashboard', 'history', 'plan', 'profile', 'payments', 'default'].includes(v),
  },
  showHeader: {
    type: Boolean,
    default: true,
  },
})
</script>

<template>
  <div class="w-full" role="status" aria-label="Loading content">
    <span class="sr-only">Loading...</span>

    <!-- Page Topbar Wireframe -->
    <div v-if="showHeader" class="mb-8 flex flex-col gap-3">
      <div class="skeleton-shimmer h-9 w-52 rounded-xl" />
      <div class="skeleton-shimmer h-4 w-80 max-w-full rounded-lg" />
    </div>

    <!-- DASHBOARD WIREFRAME -->
    <div v-if="variant === 'dashboard'" class="flex flex-col gap-5">
      <!-- Top Row: Controls + Verdict/Logs -->
      <div class="grid gap-5 xl:grid-cols-12">
        <div class="flex flex-col gap-6 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-6 xl:col-span-5">
          <div class="flex items-center gap-5">
            <div class="skeleton-shimmer size-[96px] shrink-0 rounded-full" />
            <div class="flex flex-1 flex-col gap-3">
              <div class="skeleton-shimmer h-4 w-32 rounded-md" />
              <div class="skeleton-shimmer h-3 w-full rounded-full" />
            </div>
          </div>
          <div class="flex flex-col gap-3">
            <div class="skeleton-shimmer h-10 w-full rounded-xl" />
            <div class="skeleton-shimmer h-10 w-full rounded-xl" />
            <div class="skeleton-shimmer h-6 w-full rounded-full" />
          </div>
        </div>

        <div class="flex flex-col gap-5 xl:col-span-7">
          <div class="flex flex-col items-center justify-center gap-4 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 px-6 py-10">
            <div class="skeleton-shimmer h-5 w-28 rounded-full" />
            <div class="skeleton-shimmer h-12 w-48 rounded-2xl" />
            <div class="skeleton-shimmer h-4 w-64 max-w-full rounded-lg" />
          </div>
          <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-5">
            <div class="skeleton-shimmer h-4 w-28 rounded-md" />
            <div class="skeleton-shimmer h-3.5 w-full rounded-md" />
            <div class="skeleton-shimmer h-3.5 w-5/6 rounded-md" />
          </div>
        </div>
      </div>

      <!-- Middle StatsRow -->
      <div class="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div
          v-for="n in 4"
          :key="n"
          class="flex flex-col gap-3 rounded-2xl border-2 border-back-secondary bg-back-secondary/30 p-5"
        >
          <div class="skeleton-shimmer h-3.5 w-24 rounded-md" />
          <div class="skeleton-shimmer h-8 w-20 rounded-lg" />
        </div>
      </div>

      <!-- Bottom Row: Chart + Live Table -->
      <div class="grid gap-5 xl:grid-cols-3">
        <div class="flex flex-col justify-between gap-4 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-6 xl:col-span-1">
          <div class="skeleton-shimmer h-5 w-36 rounded-md" />
          <div class="flex h-36 items-end gap-3 pt-4">
            <div v-for="b in 7" :key="b" class="skeleton-shimmer flex-1 rounded-t-lg" :style="{ height: `${30 + ((b * 19) % 65)}%` }" />
          </div>
        </div>
        <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-6 xl:col-span-2">
          <div class="skeleton-shimmer h-5 w-40 rounded-md" />
          <div v-for="r in 4" :key="r" class="skeleton-shimmer h-10 w-full rounded-xl" />
        </div>
      </div>
    </div>

    <!-- HISTORY WIREFRAME -->
    <div v-else-if="variant === 'history'" class="flex flex-col gap-6">
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="n in 4" :key="n" class="flex flex-col gap-3 rounded-2xl border-2 border-back-secondary bg-back-secondary/30 p-5">
          <div class="skeleton-shimmer h-3.5 w-24 rounded-md" />
          <div class="skeleton-shimmer h-8 w-16 rounded-lg" />
        </div>
      </div>
      <div class="flex flex-col gap-3 sm:flex-row">
        <div class="skeleton-shimmer h-11 flex-1 rounded-xl" />
        <div class="skeleton-shimmer h-11 w-full rounded-xl sm:w-44" />
      </div>
      <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-5">
        <div class="skeleton-shimmer h-9 w-full rounded-lg" />
        <div v-for="r in 6" :key="r" class="skeleton-shimmer h-12 w-full rounded-xl" />
      </div>
    </div>

    <!-- PLAN & BILLING WIREFRAME -->
    <div v-else-if="variant === 'plan'" class="flex flex-col gap-8">
      <div class="grid gap-6 lg:grid-cols-2">
        <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-6">
          <div class="skeleton-shimmer h-3.5 w-24 rounded-md" />
          <div class="skeleton-shimmer h-9 w-36 rounded-xl" />
        </div>
        <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-6">
          <div class="skeleton-shimmer h-3.5 w-20 rounded-md" />
          <div class="skeleton-shimmer h-4 w-44 rounded-md" />
          <div class="skeleton-shimmer mt-1 h-2.5 w-full rounded-full" />
        </div>
      </div>

      <div class="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
        <div v-for="c in 4" :key="c" class="flex flex-col gap-4 rounded-2xl border-2 border-back-secondary bg-back-secondary/30 p-6">
          <div class="skeleton-shimmer h-6 w-24 rounded-lg" />
          <div class="skeleton-shimmer h-9 w-32 rounded-xl" />
          <div class="my-2 h-px bg-white/10" />
          <div v-for="f in 4" :key="f" class="skeleton-shimmer h-4 w-full rounded-md" />
          <div class="skeleton-shimmer mt-4 h-11 w-full rounded-full" />
        </div>
      </div>

      <div class="flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-5">
        <div class="skeleton-shimmer h-5 w-36 rounded-md" />
        <div v-for="r in 3" :key="r" class="skeleton-shimmer h-11 w-full rounded-xl" />
      </div>
    </div>

    <!-- PAYMENTS TABLE ONLY WIREFRAME -->
    <div v-else-if="variant === 'payments'" class="mt-5 flex flex-col gap-3 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-5">
      <div class="skeleton-shimmer h-8 w-full rounded-lg" />
      <div v-for="r in 3" :key="r" class="skeleton-shimmer h-11 w-full rounded-xl" />
    </div>

    <!-- PROFILE WIREFRAME -->
    <div v-else-if="variant === 'profile'" class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]">
      <div class="flex flex-col items-center gap-4 rounded-3xl border-2 border-white/10 bg-white/[0.03] p-8">
        <div class="skeleton-shimmer size-24 rounded-full" />
        <div class="skeleton-shimmer h-6 w-40 rounded-lg" />
        <div class="skeleton-shimmer h-4 w-52 rounded-md" />
        <div class="skeleton-shimmer mt-3 h-16 w-full rounded-2xl" />
        <div class="skeleton-shimmer mt-2 h-11 w-full rounded-full" />
      </div>

      <div class="flex flex-col gap-6">
        <div class="flex flex-col gap-4 rounded-3xl border-2 border-white/10 bg-white/[0.03] p-8">
          <div class="skeleton-shimmer h-6 w-44 rounded-lg" />
          <div class="skeleton-shimmer h-12 w-full rounded-xl" />
          <div class="skeleton-shimmer h-12 w-full rounded-xl" />
          <div class="skeleton-shimmer h-12 w-full rounded-xl" />
          <div class="skeleton-shimmer ml-auto h-11 w-36 rounded-full" />
        </div>
        <div class="flex flex-col gap-4 rounded-3xl border-2 border-white/10 bg-white/[0.03] p-8">
          <div class="skeleton-shimmer h-6 w-40 rounded-lg" />
          <div class="skeleton-shimmer h-12 w-full rounded-xl" />
          <div class="skeleton-shimmer h-12 w-full rounded-xl" />
        </div>
      </div>
    </div>

    <!-- DEFAULT WIREFRAME -->
    <div v-else class="flex flex-col gap-4 rounded-3xl border-2 border-back-secondary bg-back-secondary/30 p-8">
      <div class="skeleton-shimmer h-7 w-56 rounded-lg" />
      <div class="skeleton-shimmer h-4 w-full rounded-md" />
      <div class="skeleton-shimmer h-4 w-3/4 rounded-md" />
      <div class="skeleton-shimmer mt-4 h-36 w-full rounded-2xl" />
    </div>
  </div>
</template>
