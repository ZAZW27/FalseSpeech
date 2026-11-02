<script setup>
import { ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AuthLayout from '@/components/layout/AuthLayout.vue'
import BrandPanel from '@/pages/login/BrandPanel.vue'
import FormField from '@/components/ui/inputs/FormField.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import Icon from '@/components/ui/icons/Icon.vue'

const API_URL = `${import.meta.env.VITE_API_URL ?? 'http://localhost:7860'}/api/auth/login`
const TOKEN_KEY = 'access_token'

const router = useRouter()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

const submit = async () => {
  if (isLoading.value) return
  errorMessage.value = ''

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
</script>

<template>
  <AuthLayout>
    <template #brand>
      <BrandPanel />
    </template>

    <div
      class="rounded-[28px] border border-navy-900/10 bg-white p-6 shadow-[0_20px_60px_rgba(7,20,51,0.08)] sm:p-[45px]"
    >
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-green">Welcome back</p>
      <h1 class="mt-2.5 text-[28px] font-extrabold leading-tight text-navy-900 sm:text-[32px]">
        Log in to False Speech
      </h1>
      <p class="mt-3 text-sm text-navy-900/70">
        Don't have an account?
        <RouterLink to="/subscription" class="font-semibold text-brand-green hover:underline">Sign up</RouterLink>
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
            <a href="#" class="text-[13px] font-medium text-brand-green hover:underline" @click.prevent>
              Forgot password?
            </a>
          </template>
        </FormField>

        <p
          v-if="errorMessage"
          class="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
          role="alert"
        >
          {{ errorMessage }}
        </p>

        <BaseButton type="submit" variant="dark" size="lg" block class="!h-[54px]" :disabled="isLoading">
          {{ isLoading ? 'Logging in...' : 'Log in' }}
        </BaseButton>
      </form>

      <div class="my-6 flex items-center gap-4 text-sm text-navy-900/50" aria-hidden="true">
        <span class="h-px flex-1 bg-navy-900/10" />
        or
        <span class="h-px flex-1 bg-navy-900/10" />
      </div>

      <!-- Not part of the API contract yet, so this button has no handler. -->
      <BaseButton type="button" variant="outline" size="lg" block class="!h-[54px]">
        <span class="flex size-[22px] items-center justify-center rounded-full bg-[#1a73e8] text-xs font-bold text-white">
          G
        </span>
        Continue with Google
      </BaseButton>

      <p class="mt-6 flex items-center justify-center gap-2 text-center text-[13px] text-navy-900/60">
        <span class="text-brand-green"><Icon name="shield" :size="16" /></span>
        Audio is processed in memory and never stored.
      </p>
    </div>
  </AuthLayout>
</template>
