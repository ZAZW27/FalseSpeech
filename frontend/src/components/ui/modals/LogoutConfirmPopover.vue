<script setup>
defineProps({
  open: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  positionClass: { type: String, default: 'bottom-full left-0 right-0 mb-2' },
})

defineEmits(['cancel', 'confirm'])
</script>

<template>
  <Transition name="modal-fade">
    <div
      v-if="open"
      role="menu"
      :class="[
        'absolute z-50 rounded-2xl border-2 border-back-secondary bg-back-prime p-3.5 text-left shadow-[0_18px_45px_rgba(0,0,0,0.55)]',
        positionClass,
      ]"
    >
      <p class="text-xs font-bold text-slate-100">Log out of False Speech?</p>
      <p class="mt-0.5 text-[11px] leading-relaxed text-slate-400">Your local session will be cleared.</p>
      <div class="mt-3 flex items-center justify-end gap-2">
        <button
          type="button"
          class="rounded-xl border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:bg-white/15 hover:text-white"
          @click="$emit('cancel')"
        >
          Cancel
        </button>
        <button
          type="button"
          :disabled="busy"
          class="rounded-xl border border-red-400/40 bg-red-500/20 px-3 py-1.5 text-xs font-bold text-red-200 transition hover:border-red-400/70 hover:bg-red-500/35 disabled:opacity-50"
          @click="$emit('confirm')"
        >
          {{ busy ? 'Logging out...' : 'Log out' }}
        </button>
      </div>
    </div>
  </Transition>
</template>
