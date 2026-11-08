<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import BrandPanel from '@/pages/login/BrandPanel.vue'
import FormField from '@/components/ui/inputs/FormField.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import Icon from '@/components/ui/icons/Icon.vue'

const API_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:7860'}/api/auth/register`
const REDIRECT_DELAY_MS = 1500

const router = useRouter()

const name = ref('')
const email = ref('')
const phone = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
let redirectTimer = null

// FastAPI style errors: detail is a string (409, 400) or a list of { msg } (422).
const readError = (data) => {
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) {
    const messages = data.detail.map((item) => item?.msg).filter(Boolean)
    if (messages.length) return messages.join('. ')
  }
  return 'Registration failed. Please try again.'
}

const submit = async () => {
  if (isLoading.value || successMessage.value) return
  errorMessage.value = ''

  if (!name.value.trim() || !email.value.trim() || !phone.value.trim() || !password.value) {
    errorMessage.value = 'Please fill in all fields.'
    return
  }
  if (!emailPattern.test(email.value.trim())) {
    errorMessage.value = 'Please enter a valid email address.'
    return
  }

  isLoading.value = true

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: name.value.trim(),
        email: email.value.trim(),
        phone: phone.value.trim(),
        password: password.value,
      }),
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      errorMessage.value = readError(data)
      return
    }

    // 201 Created: show the message briefly, then go to the login page.
    successMessage.value = 'Registration successful! Please login.'
    redirectTimer = setTimeout(() => router.push('/login'), REDIRECT_DELAY_MS)
  } catch {
    errorMessage.value = 'Cannot reach the server. Please check your connection and try again.'
  } finally {
    isLoading.value = false
  }
}

onBeforeUnmount(() => clearTimeout(redirectTimer))
</script>

<template>
  <AuthLayout>
    <template #brand>
      <BrandPanel
        title="Create your account."
        subtitle="Join False Speech on the Free plan and run your first voice check in minutes."
      />
    </template>

    <div
      class="rounded-[28px] border border-back-prime/10 bg-white p-6 shadow-[0_20px_60px_rgba(7,20,51,0.08)] sm:p-[45px]"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-green">Get started</p>
      <h1 class="mt-2.5 text-[28px] font-extrabold leading-tight text-back-prime sm:text-[32px]">
        Sign up for False Speech
      </h1>
      <p class="mt-3 text-sm text-back-prime/70">New accounts start on the Free plan.</p>

      <form class="mt-8 flex flex-col gap-5" novalidate @submit.prevent="submit">
        <FormField
          id="register-name"
          v-model="name"
          tone="light"
          label="Full Name"
          placeholder="Your full name"
          autocomplete="name"
        />
        <FormField
          id="register-email"
          v-model="email"
          tone="light"
          type="email"
          label="Email"
          placeholder="you@example.com"
          autocomplete="email"
        />
        <FormField
          id="register-phone"
          v-model="phone"
          tone="light"
          type="tel"
          label="Phone Number"
          placeholder="0811122233"
          autocomplete="tel"
        />
        <FormField
          id="register-password"
          v-model="password"
          tone="light"
          type="password"
          label="Password"
          placeholder="Create a password"
          autocomplete="new-password"
        />

        <p
          v-if="errorMessage"
          class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
          role="alert"
        >
          {{ errorMessage }}
        </p>
        <p
          v-if="successMessage"
          class="rounded-xl border border-brand-green/30 bg-brand-green/10 px-4 py-3 text-sm font-medium text-brand-green"
          role="status"
        >
          {{ successMessage }}
        </p>

        <BaseButton
          type="submit"
          variant="dark"
          size="lg"
          block
          class="!h-[54px]"
          :disabled="isLoading || !!successMessage"
        >
          {{ isLoading ? 'Creating account...' : 'Create account' }}
        </BaseButton>
      </form>

      <p class="mt-6 text-center text-sm text-back-prime/70">
        Already have an account?
        <RouterLink to="/login" class="font-semibold text-blue-600 hover:underline">Login here</RouterLink>
      </p>

      <p class="mt-6 flex items-center justify-center gap-2 text-center text-[13px] text-back-prime/60">
        <span class="text-brand-green"><Icon name="shield" :size="16" /></span>
        Audio is processed in memory and never stored.
      </p>
    </div>
  </AuthLayout>
</template>
