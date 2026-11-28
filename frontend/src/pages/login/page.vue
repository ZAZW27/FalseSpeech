<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { API_BASE } from '@/assets/js/api'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import BrandPanel from '@/pages/login/BrandPanel.vue'
import FormField from '@/components/ui/inputs/FormField.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import BaseModal from '@/components/ui/modals/BaseModal.vue'
import Icon from '@/components/ui/icons/Icon.vue'

const API_URL = `${(import.meta.env.VITE_API_URL || 'https://falsespeech.putrahomelab.com').replace(/\/+$/, '')}/api/auth/login`
const TOKEN_KEY = 'access_token'

const router = useRouter()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const submit = async () => {
  if (isLoading.value) return
  errorMessage.value = ''
  successMessage.value = ''

  if (!email.value.trim() || !password.value) {
    errorMessage.value = 'Please enter your email or phone number and your password.'
    return
  }

  isLoading.value = true

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email_or_phone: email.value.trim(),
        password: password.value,
      }),
    })

    const data = await response.json().catch(() => null)

    if (!response.ok) {
      // 401 returns { detail: "..." }. Other errors may use a different shape.
      errorMessage.value =
        typeof data?.detail === 'string' ? data.detail : 'Login failed. Please try again.'
      return
    }

    localStorage.setItem(TOKEN_KEY, data.access_token)
    await router.push('/dashboard')
  } catch {
    errorMessage.value = 'Cannot reach the server. Please check your connection and try again.'
  } finally {
    isLoading.value = false
  }
}

// ---------- Forgot password (modal, 2 steps) ----------
// Step 1: POST /api/auth/forgot-password { email }
// Step 2: POST /api/auth/reset-password { email, otp_code, new_password }
const forgotOpen = ref(false)
const forgotStep = ref('email') // 'email' | 'reset'
const forgotEmail = ref('')
const otpCode = ref('')
const newPassword = ref('')
const forgotLoading = ref(false)
const forgotError = ref('')
const forgotInfo = ref('')

const openForgot = () => {
  forgotStep.value = 'email'
  forgotEmail.value = email.value.includes('@') ? email.value.trim() : ''
  otpCode.value = ''
  newPassword.value = ''
  forgotError.value = ''
  forgotInfo.value = ''
  forgotOpen.value = true
}

const postJson = async (path, payload) => {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  const data = await response.json().catch(() => null)

  if (response.ok) return data
  if (response.status === 429) throw new Error('Too many attempts. Please wait a minute and try again.')
  // FastAPI sends detail as a string, or as a list for validation errors.
  if (typeof data?.detail === 'string') throw new Error(data.detail)
  if (response.status === 422) throw new Error('Please check the values you entered.')
  throw new Error('Something went wrong. Please try again.')
}

const sendCode = async () => {
  if (forgotLoading.value) return
  forgotError.value = ''
  forgotInfo.value = ''

  if (!forgotEmail.value.trim()) {
    forgotError.value = 'Please enter your email.'
    return
  }

  forgotLoading.value = true
  try {
    await postJson('/api/auth/forgot-password', { email: forgotEmail.value.trim() })
    forgotStep.value = 'reset'
    forgotInfo.value = 'If this email is registered, a 6-digit code was sent. It is valid for 5 minutes.'
  } catch (error) {
    forgotError.value = error.message === 'Failed to fetch'
      ? 'Cannot reach the server. Please check your connection.'
      : error.message
  } finally {
    forgotLoading.value = false
  }
}

const resetPassword = async () => {
  if (forgotLoading.value) return
  forgotError.value = ''
  forgotInfo.value = ''

  if (!/^\d{6}$/.test(otpCode.value.trim())) {
    forgotError.value = 'The code is 6 digits.'
    return
  }
  if (newPassword.value.length < 8) {
    forgotError.value = 'The new password must be at least 8 characters.'
    return
  }

  forgotLoading.value = true
  try {
    await postJson('/api/auth/reset-password', {
      email: forgotEmail.value.trim(),
      otp_code: otpCode.value.trim(),
      new_password: newPassword.value,
    })

    // Back to the login form with the email filled in.
    email.value = forgotEmail.value.trim()
    password.value = ''
    errorMessage.value = ''
    successMessage.value = 'Your password was changed. Log in with your new password.'
    forgotOpen.value = false
  } catch (error) {
    forgotError.value = error.message === 'Failed to fetch'
      ? 'Cannot reach the server. Please check your connection.'
      : error.message
  } finally {
    forgotLoading.value = false
  }
}

const backToEmailStep = () => {
  forgotStep.value = 'email'
  forgotError.value = ''
  forgotInfo.value = ''
  otpCode.value = ''
  newPassword.value = ''
}
</script>

<template>
  <AuthLayout>
    <template #brand>
      <BrandPanel />
    </template>

    <div
      class="rounded-[28px] border border-back-prime/10 bg-white p-6 shadow-[0_20px_60px_rgba(7,20,51,0.08)] sm:p-[45px]"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-green">Welcome back</p>
      <h1 class="mt-2.5 text-[28px] font-extrabold leading-tight text-back-prime sm:text-[32px]">
        Log in to False Speech
      </h1>
      <p class="mt-3 text-sm text-back-prime/70">
        Don't have an account?
        <RouterLink to="/register" class="font-semibold text-blue-600 hover:underline">Sign up</RouterLink>
      </p>

      <form class="mt-8 flex flex-col gap-6" novalidate @submit.prevent="submit">
        <FormField
          id="login-email"
          v-model="email"
          tone="light"
          label="Email"
          placeholder="you@example.com"
          autocomplete="username"
        />

        <FormField
          id="login-password"
          v-model="password"
          tone="light"
          type="password"
          label="Password"
          placeholder="Enter your password"
          autocomplete="current-password"
        >
          <template #label-extra>
            <button
              type="button"
              class="text-[13px] font-medium text-blue-600 hover:underline"
              @click="openForgot"
            >
              Forgot password?
            </button>
          </template>
        </FormField>

        <p
          v-if="successMessage"
          class="rounded-xl border border-brand-green/40 bg-brand-green/10 px-4 py-3 text-sm font-medium text-back-prime"
          role="status"
        >
          {{ successMessage }}
        </p>

        <p
          v-if="errorMessage"
          class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
          role="alert"
        >
          {{ errorMessage }}
        </p>

        <BaseButton type="submit" variant="dark" size="lg" block class="!h-[54px]" :disabled="isLoading">
          {{ isLoading ? 'Logging in...' : 'Log in' }}
        </BaseButton>
      </form>

      <p class="mt-6 flex items-center justify-center gap-2 text-center text-[13px] text-back-prime/60">
        <span class="text-back-prime/50"><Icon name="shield" :size="16" /></span>
        Audio is processed in memory and never stored.
      </p>
    </div>

    <!-- Forgot password -->
    <BaseModal v-model="forgotOpen" label="Reset password">
      <div class="rounded-t-3xl bg-white p-6 text-back-prime sm:p-8 md:rounded-3xl">
        <div class="flex items-start justify-between gap-4">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-green">
              Step {{ forgotStep === 'email' ? 1 : 2 }} of 2
            </p>
            <h2 class="mt-2 text-2xl font-extrabold">
              {{ forgotStep === 'email' ? 'Forgot your password?' : 'Set a new password' }}
            </h2>
          </div>
          <button
            type="button"
            class="flex size-9 shrink-0 items-center justify-center rounded-full text-back-prime/60 transition hover:bg-back-prime/10"
            aria-label="Close"
            @click="forgotOpen = false"
          >
            <Icon name="close" :size="16" />
          </button>
        </div>

        <!-- Step 1: email -->
        <form v-if="forgotStep === 'email'" class="mt-6 flex flex-col gap-5" novalidate @submit.prevent="sendCode">
          <p class="text-sm text-back-prime/70">
            Enter the email of your account. We will send you a 6-digit code.
          </p>

          <FormField
            id="forgot-email"
            v-model="forgotEmail"
            tone="light"
            type="email"
            label="Email"
            placeholder="you@example.com"
            autocomplete="email"
          />

          <p
            v-if="forgotError"
            class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
            role="alert"
          >
            {{ forgotError }}
          </p>

          <BaseButton type="submit" variant="dark" size="lg" block class="!h-[54px]" :disabled="forgotLoading">
            {{ forgotLoading ? 'Sending...' : 'Send code' }}
          </BaseButton>
        </form>

        <!-- Step 2: code and new password -->
        <form v-else class="mt-6 flex flex-col gap-5" novalidate @submit.prevent="resetPassword">
          <p
            v-if="forgotInfo"
            class="rounded-xl border border-back-prime/10 bg-back-prime/5 px-4 py-3 text-sm text-back-prime/80"
            role="status"
          >
            {{ forgotInfo }}
          </p>

          <FormField
            id="forgot-otp"
            v-model="otpCode"
            tone="light"
            label="6-digit code"
            placeholder="123456"
            autocomplete="one-time-code"
          />

          <FormField
            id="forgot-new-password"
            v-model="newPassword"
            tone="light"
            type="password"
            label="New password"
            placeholder="At least 8 characters"
            autocomplete="new-password"
          />

          <p
            v-if="forgotError"
            class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
            role="alert"
          >
            {{ forgotError }}
          </p>

          <BaseButton type="submit" variant="dark" size="lg" block class="!h-[54px]" :disabled="forgotLoading">
            {{ forgotLoading ? 'Saving...' : 'Change password' }}
          </BaseButton>

          <div class="flex items-center justify-between text-[13px]">
            <button type="button" class="font-medium text-blue-600 hover:underline" @click="backToEmailStep">
              Use another email
            </button>
            <button
              type="button"
              class="font-medium text-blue-600 hover:underline disabled:opacity-50"
              :disabled="forgotLoading"
              @click="sendCode"
            >
              Send the code again
            </button>
          </div>
        </form>
      </div>
    </BaseModal>
  </AuthLayout>
</template>
