<script setup>
// Capture settings shared by the free and paid dashboards.
defineProps({
  devices: { type: Array, default: () => [] },
  // Mode and device cannot change while listening. The chunk slider always can.
  locked: { type: Boolean, default: false },
})

const mode = defineModel('mode', { type: String, default: 'monitor' })
const selectedDevice = defineModel('selectedDevice', { type: String, default: '' })
const chunkSize = defineModel('chunkSize', { type: Number, default: 10 })

const modes = [
  { value: 'monitor', label: 'Mode A: System monitor' },
  { value: 'tab', label: 'Mode B: Browser tab' },
]
</script>

<template>
  <div class="flex flex-col gap-5">
    <fieldset :disabled="locked" class="min-w-0">
      <legend class="mb-2 text-xs font-semibold uppercase tracking-wider text-secondary/70">Capture mode</legend>
      <div class="grid gap-2 sm:grid-cols-2">
        <label v-for="item in modes" :key="item.value" class="cursor-pointer">
          <input v-model="mode" type="radio" name="capture-mode" :value="item.value" class="peer sr-only" />
          <span
            class="flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-3 text-center text-sm text-white/80 transition peer-checked:border-brand-green/60 peer-checked:bg-brand-green/10 peer-checked:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-brand-green peer-disabled:opacity-50"
          >
            {{ item.label }}
          </span>
        </label>
      </div>
    </fieldset>

    <!-- Only Mode A needs an input device -->
    <div v-if="mode === 'monitor'" class="flex flex-col gap-2">
      <label for="capture-device" class="text-xs font-semibold uppercase tracking-wider text-secondary/70">
        Audio input
      </label>
      <select
        id="capture-device"
        v-model="selectedDevice"
        :disabled="locked"
        class="h-12 w-full rounded-xl border border-white/15 bg-back-prime px-4 text-sm text-white focus:border-brand-green focus:outline-none disabled:opacity-50"
      >
        <option v-if="!devices.length" value="" disabled>No audio inputs found</option>
        <option v-for="device in devices" :key="device.deviceId" :value="device.deviceId">
          {{ device.label }}
        </option>
      </select>
    </div>

    <div class="flex flex-col gap-2">
      <label for="capture-chunk" class="text-xs font-semibold uppercase tracking-wider text-secondary/70">
        Chunk size: <span class="text-sm normal-case tracking-normal text-white">{{ chunkSize }}s</span>
      </label>
      <input
        id="capture-chunk"
        v-model.number="chunkSize"
        type="range"
        min="1"
        max="15"
        step="1"
        class="h-1.5 w-full cursor-pointer accent-brand-green"
      />
    </div>
  </div>
</template>
