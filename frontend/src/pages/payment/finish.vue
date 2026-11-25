<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authFetch, clearToken } from '@/assets/js/api'
import AppLayout from '@/components/layout/AppLayout.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'

const route = useRoute()
const router = useRouter()

const orderId = computed(() => String(route.query.order_id ?? ''))
const txStatus = computed(() => String(route.query.transaction_status ?? 'settlement').toLowerCase())

const isRefreshing = ref(true)
const userTier = ref('')

const statusMeta = computed(() => {
  if (txStatus.value === 'settlement' || txStatus.value === 'capture') {
    return {
      badge: 'Payment Confirmed',
      title: 'Your subscription is active!',
      description: 'Thank you for upgrading. Your new tier and daily quota are ready to use.',
      tone: 'text-brand-green border-brand-green/40 bg-brand-green/10',
    }
  }
  if (txStatus.value === 'pending') {
    return {
      badge: 'Payment Pending',
      title: 'Waiting for payment confirmation',
      description: 'Complete your payment in Midtrans. Your account will upgrade automatically once settled.',
      tone: 'text-secondary border-secondary/40 bg-secondary/10',
    }
  }
  return {
    badge: 'Payment Incomplete',
    title: 'Payment was not completed',
    description: 'No charges were applied to your plan. You can try upgrading again at any time.',
    tone: 'text-red-400 border-red-400/40 bg-red-400/10',
  }
})

const refreshAccount = async () => {
  isRefreshing.value = true
  try {
    const res = await authFetch('/api/users/me')
    if (res.status === 401) {
      clearToken()
      router.replace('/login')
      return
    }
    if (res.ok) {
      const data = await res.json()
      userTier.value = data.tier ?? ''
    }
  } finally {
    isRefreshing.value = false
  }
}

onMounted(refreshAccount)
</script>

<template>
  <AppLayout title="Payment Status" subtitle="Midtrans checkout confirmation.">
    <section
      class="mx-auto flex max-w-[560px] flex-col items-center rounded-3xl border border-white/10 bg-white/[0.04] p-8 text-center"
    >
      <span
        :class="['rounded-full border px-4 py-1 text-xs font-bold uppercase tracking-wider', statusMeta.tone]"
      >
        {{ statusMeta.badge }}
      </span>

      <h2 class="mt-5 text-2xl font-extrabold text-white">
        {{ statusMeta.title }}
      </h2>
      <p class="mt-3 text-sm leading-relaxed text-muted">
        {{ statusMeta.description }}
      </p>

      <dl
        v-if="orderId || userTier"
        class="mt-6 w-full rounded-2xl border border-white/10 bg-back-prime/70 p-4 text-left text-sm"
      >
        <div v-if="orderId" class="flex justify-between py-1">
          <dt class="text-muted">Order ID</dt>
          <dd class="font-mono text-white">{{ orderId }}</dd>
        </div>
        <div v-if="userTier" class="flex justify-between py-1">
          <dt class="text-muted">Active Tier</dt>
          <dd class="font-bold uppercase text-brand-green">{{ userTier.replace('_', ' ') }}</dd>
        </div>
      </dl>

      <div class="mt-8 flex w-full flex-col gap-3 sm:flex-row sm:justify-center">
        <BaseButton to="/dashboard" class="w-full sm:w-auto">
          Go to Dashboard
        </BaseButton>
        <BaseButton to="/plan" variant="outlineLight" class="w-full sm:w-auto">
          View Plan &amp; Billing
        </BaseButton>
      </div>
    </section>
  </AppLayout>
</template>
