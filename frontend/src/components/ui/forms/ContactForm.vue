<script setup>
import { reactive, ref } from 'vue'
import FormField from '@/components/ui/inputs/FormField.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'

const form = reactive({ name: '', email: '', message: '' })
const errors = reactive({ name: '', email: '', message: '' })
const submitted = ref(false)

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const validate = () => {
  errors.name = form.name.trim() ? '' : 'Please enter your name.'
  errors.email = emailPattern.test(form.email) ? '' : 'Please enter a valid email address.'
  errors.message = form.message.trim().length >= 10 ? '' : 'Message must be at least 10 characters.'
  return !errors.name && !errors.email && !errors.message
}

const submit = () => {
  if (!validate()) return
  // Hook a real request in here (for example fetch to your API).
  submitted.value = true
}

const reset = () => {
  form.name = ''
  form.email = ''
  form.message = ''
  submitted.value = false
}
</script>

<template>
  <div class="rounded-3xl border border-white/10 bg-white/[0.04] p-6 md:p-10">
    <div v-if="submitted" class="flex flex-col items-start gap-4" role="status">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-lime-400">Message sent</p>
      <h2 class="text-2xl font-bold">Thank you, {{ form.name }}.</h2>
      <p class="text-muted">We received your message and will reply to {{ form.email }}.</p>
      <BaseButton variant="outlineLight" @click="reset">Send another message</BaseButton>
    </div>

    <form v-else class="flex flex-col gap-6" novalidate @submit.prevent="submit">
      <FormField
        id="contact-name"
        v-model="form.name"
        label="Name"
        placeholder="Your name"
        autocomplete="name"
        :error="errors.name"
      />
      <FormField
        id="contact-email"
        v-model="form.email"
        type="email"
        label="Email"
        placeholder="you@example.com"
        autocomplete="email"
        :error="errors.email"
      />
      <FormField
        id="contact-message"
        v-model="form.message"
        type="textarea"
        label="Message"
        placeholder="How can we help?"
        :error="errors.message"
      />

      <BaseButton type="submit" size="lg" class="self-start">Submit</BaseButton>
    </form>
  </div>
</template>
