<script setup>
import { computed } from 'vue'

// Capture settings shared by the free and paid dashboards.
const props = defineProps({
  devices: { type: Array, default: () => [] },
  verifiedDevices: { type: Array, default: () => [] },
  // Mode and device cannot change while listening. The chunk slider always can.
  locked: { type: Boolean, default: false },
})

const mode = defineModel('mode', { type: String, default: 'monitor' })
const selectedDevice = defineModel('selectedDevice', { type: String, default: '' })
const chunkSize = defineModel('chunkSize', { type: Number, default: 10 })

const verifiedSet = computed(() => new Set(props.verifiedDevices || []))
const isSelectedVerified = computed(() => verifiedSet.value.has(selectedDevice.value))
const isInternalDriver = (label) =>
  /monitor|loopback|stereo mix|what u hear|blackhole|soundflower|virtual cable|vb-audio/i.test(String(label || ''))

const modes = [
  { value: 'monitor', label: 'Mode A: System monitor' },
  { value: 'tab', label: 'Mode B: Tab / System share' },
]
</script>

<template>
  <div class="flex flex-col gap-5">
    <fieldset :disabled="locked" class="min-w-0">
      <legend class="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Capture mode</legend>
      <div class="grid gap-2 sm:grid-cols-2">
        <label v-for="item in modes" :key="item.value" class="cursor-pointer">
          <input v-model="mode" type="radio" name="capture-mode" :value="item.value" class="peer sr-only" />
          <span
            class="flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-3 text-center text-sm text-slate-300 transition hover:border-white/30 hover:text-slate-100 peer-checked:border-white/40 peer-checked:bg-white/10 peer-checked:font-semibold peer-checked:text-slate-100 peer-focus-visible:outline-2 peer-focus-visible:outline-white/40 peer-disabled:opacity-50"
          >
            {{ item.label }}
          </span>
        </label>
      </div>
    </fieldset>

    <!-- Only Mode A needs an input device -->
    <div v-if="mode === 'monitor'" class="flex flex-col gap-2">
      <div class="flex items-center justify-between gap-2">
        <label for="capture-device" class="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Audio input
        </label>
        <span
          v-if="isSelectedVerified"
          class="inline-flex items-center gap-1 rounded-full border border-white/20 bg-white/10 px-2 py-0.5 text-[10px] font-semibold text-slate-200"
        >
          ● Signal Verified
        </span>
      </div>
      <select
        id="capture-device"
        v-model="selectedDevice"
        :disabled="locked"
        class="h-12 w-full rounded-xl border border-white/15 bg-back-prime px-4 text-sm text-slate-100 transition hover:border-white/30 focus:border-white/40 focus:outline-none disabled:opacity-50"
      >
        <option v-if="!devices.length" value="" disabled>No audio inputs found</option>
        <option
          v-for="device in devices"
          :key="device.deviceId"
          :value="device.deviceId"
          :style="verifiedSet.has(device.deviceId) ? 'color:#B7D894;font-weight:700;' : ''"
        >
          {{ verifiedSet.has(device.deviceId) ? '● ' : '' }}[{{ isInternalDriver(device.label) ? 'Internal' : 'External' }}] {{ device.label }}
        </option>
      </select>
    </div>

    <div class="flex flex-col gap-2">
      <label for="capture-chunk" class="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Chunk size: <span class="text-sm normal-case tracking-normal text-slate-100">{{ chunkSize }}s</span>
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
