<script setup>
import { ref, watch } from 'vue'
import BaseModal from '@/components/ui/modals/BaseModal.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'

const props = defineProps({
  modelValue: { type: Boolean, required: true },
  plan: { type: Object, required: true },
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const confirmed = ref(false)

// Start from the confirmation step every time the modal opens.
watch(
  () => props.modelValue,
  (open) => {
    if (open) confirmed.value = false
  },
)

const close = () => emit('update:modelValue', false)

const confirm = () => {
  confirmed.value = true
  emit('confirm', props.plan)
}
</script>

<template>
  <BaseModal :model-value="modelValue" label="Confirm plan" @update:model-value="emit('update:modelValue', $event)">
    <div class="p-8">
      <template v-if="!confirmed">
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-lime-400">Confirm plan</p>
        <h2 class="mt-4 text-2xl font-bold">Switch to {{ plan.name }}?</h2>
        <p class="mt-3 text-sm text-muted">
          You will pay {{ plan.price }} ({{ plan.period }}). You can change your plan at any time.
        </p>

        <div class="mt-8 flex flex-col gap-3">
          <BaseButton block @click="confirm">Confirm</BaseButton>
          <BaseButton variant="ghost" block size="sm" @click="close">Cancel</BaseButton>
        </div>
      </template>

      <template v-else>
        <p class="text-xs font-semibold uppercase tracking-[0.2em] text-lime-400">Done</p>
        <h2 class="mt-4 text-2xl font-bold">{{ plan.name }} selected</h2>
        <p class="mt-3 text-sm text-muted">Your choice has been recorded for this demo.</p>
        <BaseButton variant="outlineLight" block class="mt-8" @click="close">Close</BaseButton>
      </template>
    </div>
  </BaseModal>
</template>
