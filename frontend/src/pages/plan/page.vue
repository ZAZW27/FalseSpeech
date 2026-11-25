<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { plans } from '@/assets/data/plans'
import { authFetch, clearToken } from '@/assets/js/api'
import { formatDateTime, formatDuration, toPercent } from '@/assets/js/format'
import AppLayout from '@/components/layout/AppLayout.vue'
import PricingCard from '@/components/ui/cards/PricingCard.vue'
import BaseButton from '@/components/ui/buttons/BaseButton.vue'
import BaseModal from '@/components/ui/modals/BaseModal.vue'

const router = useRouter()

// Lowest to highest. Used to decide between "Upgrade" and "Downgrade".
const TIER_RANK = { free: 0, pro: 1, pro_max: 2, lifetime: 3 }

// plans.js uses "pro-max", the API uses "pro_max".
const toTier = (planId) => planId.replace('-', '_')

const upgradingTier = ref('')
const errorMessage = ref('')
const noticeMessage = ref('')

const tierLabel = (tier) => plans.find((plan) => toTier(plan.id) === tier)?.name ?? tier

const actionFor = (user, plan) => {
  const tier = toTier(plan.id)
  if (tier === user.tier) return { label: 'Current Plan', disabled: true, isUpgrade: false }
  const isUpgrade = (TIER_RANK[tier] ?? 0) > (TIER_RANK[user.tier] ?? 0)
  return { label: isUpgrade ? 'Upgrade' : 'Downgrade', disabled: false, isUpgrade }
}

// Reads the error text from a failed response. FastAPI uses a string for "detail".
const readError = async (response) => {
  const body = await response.json().catch(() => ({}))
  return typeof body.detail === 'string' ? body.detail : `Request failed with status ${response.status}`
}

const handleUnauthorized = () => {
  clearToken()
  router.replace('/login')
}

// ---------- Upgrade ----------
// POST /api/subscription/upgrade -> { payment_url }
const upgrade = async (targetTier) => {
  errorMessage.value = ''
  noticeMessage.value = ''
  upgradingTier.value = targetTier

  try {
    const response = await authFetch('/api/subscription/upgrade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_tier: targetTier }),
    })

    if (response.status === 401) return handleUnauthorized()
    if (!response.ok) throw new Error(await readError(response))

    const data = await response.json()
    if (!data.payment_url) throw new Error('Payment link was not returned by the server.')
    window.location.href = data.payment_url
  } catch (error) {
    errorMessage.value = `Could not start the payment. ${error.message}`
    upgradingTier.value = ''
  }
}

// ---------- Downgrade (confirm first, then POST /api/subscription/downgrade) ----------
const downgradePlan = ref(null) // the plan the user wants to move to, null when the dialog is closed
const downgradeOpen = ref(false)
const isDowngrading = ref(false)
const downgradeError = ref('')

const askDowngrade = (plan) => {
  errorMessage.value = ''
  noticeMessage.value = ''
  downgradeError.value = ''
  downgradePlan.value = plan
  downgradeOpen.value = true
}

const closeDowngrade = () => {
  if (isDowngrading.value) return
  downgradeOpen.value = false
}

// refresh comes from AppLayout and reloads GET /api/users/me.
const confirmDowngrade = async (refresh) => {
  if (!downgradePlan.value || isDowngrading.value) return
  isDowngrading.value = true
  downgradeError.value = ''

  try {
    const response = await authFetch('/api/subscription/downgrade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_tier: toTier(downgradePlan.value.id) }),
    })

    if (response.status === 401) return handleUnauthorized()
    if (!response.ok) throw new Error(await readError(response))

    noticeMessage.value = `Your plan is now ${downgradePlan.value.name}.`
    downgradeOpen.value = false
    await refresh()
  } catch (error) {
    downgradeError.value = error.message === 'Failed to fetch'
      ? 'Cannot reach the server. Please check your connection.'
      : error.message
  } finally {
    isDowngrading.value = false
  }
}

const handleAction = (plan, action) => {
  if (action.isUpgrade) {
    upgrade(toTier(plan.id))
    return
  }
  askDowngrade(plan)
}

// ---------- Payment history ----------
// GET /api/billing/history -> [{ invoice_id, order_id, amount_idr, status, issued_at, paid_at, tier }]
const payments = ref([])
const historyLoading = ref(true)
const historyError = ref('')

const formatRupiah = (amount) => `Rp${new Intl.NumberFormat('id-ID').format(Number(amount) || 0)}`

const loadPayments = async () => {
  historyLoading.value = true
  historyError.value = ''

  try {
    const response = await authFetch('/api/billing/history')

    if (response.status === 401) return handleUnauthorized()
    if (!response.ok) throw new Error(`Request failed with status ${response.status}`)

    const data = await response.json()
    payments.value = (Array.isArray(data) ? data : []).map((item) => ({
      id: item.invoice_id,
      orderId: item.order_id,
      date: formatDateTime(item.paid_at ?? item.issued_at),
      description: `${tierLabel(item.tier)} plan`,
      amount: formatRupiah(item.amount_idr),
      status: item.status === 'success' ? 'Paid' : item.status === 'pending' ? 'Pending' : 'Failed',
    }))
  } catch {
    historyError.value = 'Could not load your payment history.'
  } finally {
    historyLoading.value = false
  }
}

// GET /api/billing/invoice/{order_id} returns HTML. It needs the JWT, so a plain link would not work.
// The HTML becomes a Blob and opens in a new tab.
const viewingOrder = ref('')

const viewInvoice = async (payment) => {
  if (viewingOrder.value) return
  errorMessage.value = ''
  viewingOrder.value = payment.orderId

  // Open the tab right away (inside the click) so the browser does not block the popup.
  const tab = window.open('', '_blank')

  try {
    const response = await authFetch(`/api/billing/invoice/${encodeURIComponent(payment.orderId)}`)

    if (response.status === 401) {
      tab?.close()
      return handleUnauthorized()
    }
    if (!response.ok) throw new Error(await readError(response))

    const html = await response.text()
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)

    if (tab) tab.location.href = url
    else window.open(url, '_blank')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (error) {
    tab?.close()
    errorMessage.value = `Could not open the invoice. ${error.message}`
  } finally {
    viewingOrder.value = ''
  }
}

const statusClasses = {
  Paid: 'bg-brand-green/15 text-brand-green',
  Pending: 'bg-secondary/10 text-secondary',
  Failed: 'bg-red-400/15 text-red-300',
}

const historyColumns = 'grid grid-cols-[1.4fr_2fr_1.2fr_1fr_1fr] items-center gap-4'

onMounted(loadPayments)
</script>

<template>
  <AppLayout title="Plan & Billing" subtitle="Manage your subscription and review your usage.">
    <template #default="{ user, refresh }">
      <div class="flex flex-col gap-8 rounded-3xl bg-back-prime p-5 md:p-8">
        <p
          v-if="errorMessage"
          class="rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-sm font-medium text-red-300"
          role="alert"
        >
          {{ errorMessage }}
        </p>
        <p
          v-if="noticeMessage"
          class="rounded-xl border border-back-secondary bg-back-secondary/40 px-4 py-3 text-sm text-secondary"
          role="status"
        >
          {{ noticeMessage }}
        </p>

        <!-- Top section: two columns on desktop -->
        <div class="grid gap-6 lg:grid-cols-2">
          <!-- Current plan -->
          <section class="rounded-3xl border border-back-secondary bg-back-secondary/40 p-6">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Current plan</p>
            <h2 class="mt-2 text-3xl font-extrabold text-white">{{ tierLabel(user.tier) }}</h2>
          </section>

          <!-- Usage -->
          <section class="rounded-3xl border border-back-secondary bg-back-secondary/40 p-6">
            <p class="text-[11px] font-semibold uppercase tracking-wider text-secondary/70">Usage</p>

            <!-- Lifetime: no quota, show plain accent text instead of the bar -->
            <p v-if="user.tier === 'lifetime'" class="mt-3 text-3xl font-extrabold uppercase tracking-wide text-brand-green">
              UNLIMITED POWER
            </p>

            <div v-else class="mt-3">
              <p class="text-sm font-semibold tabular-nums text-white">
                {{ formatDuration(user.quota_used) }} of {{ formatDuration(user.quota_limit) }} used
              </p>
              <div
                class="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-back-prime"
                role="progressbar"
                aria-label="Daily quota used"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="toPercent(user.quota_used, user.quota_limit)"
              >
                <div
                  class="h-full rounded-full bg-brand-green transition-all"
                  :style="{ width: `${toPercent(user.quota_used, user.quota_limit)}%` }"
                />
              </div>
              <p class="mt-2 text-xs text-secondary/70">{{ toPercent(user.quota_used, user.quota_limit) }}% of your quota</p>
            </div>
          </section>
        </div>

        <!-- Compare plans -->
        <section>
          <h2 class="text-xl font-bold text-white">Compare plans</h2>

          <!-- No gap: the cards overlap by 1px and share their borders -->
          <div class="mt-5 grid pl-px pt-px md:grid-cols-2 xl:grid-cols-4">
            <PricingCard v-for="plan in plans" :key="plan.id" :plan="plan" dark>
              <template #cta>
                <BaseButton
                  size="lg"
                  block
                  class="mt-10"
                  :class="
                    actionFor(user, plan).disabled
                      ? '!border !border-white/20 !bg-transparent !bg-none !text-secondary !shadow-none'
                      : '!bg-brand-green !bg-none !text-back-prime !shadow-none hover:!brightness-105'
                  "
                  :disabled="actionFor(user, plan).disabled || upgradingTier !== ''"
                  @click="handleAction(plan, actionFor(user, plan))"
                >
                  {{ upgradingTier === toTier(plan.id) ? 'Redirecting...' : actionFor(user, plan).label }}
                </BaseButton>
              </template>
            </PricingCard>
          </div>
        </section>

        <!-- Payment history -->
        <section>
          <h2 class="text-xl font-bold text-white">Payment history</h2>

          <p v-if="historyLoading" class="mt-5 text-sm text-secondary/70" role="status">Loading payments...</p>

          <div v-else-if="historyError" class="mt-5 flex flex-wrap items-center gap-4" role="alert">
            <p class="text-sm text-red-300">{{ historyError }}</p>
            <BaseButton size="sm" variant="outlineLight" @click="loadPayments">Try again</BaseButton>
          </div>

          <p
            v-else-if="!payments.length"
            class="mt-5 rounded-3xl border border-back-secondary px-6 py-10 text-center text-sm text-secondary/70"
          >
            No payments yet. Your invoices will appear here after you upgrade.
          </p>

          <div v-else class="mt-5 rounded-3xl border border-back-secondary">
            <div class="overflow-x-auto">
              <div class="min-w-[640px]" role="table" aria-label="Payment history">
                <div
                  :class="[historyColumns, 'border-b border-back-secondary px-6 py-4 text-[11px] font-semibold uppercase tracking-wider text-secondary/70']"
                  role="row"
                >
                  <span role="columnheader">Date</span>
                  <span role="columnheader">Description</span>
                  <span role="columnheader">Amount</span>
                  <span role="columnheader">Status</span>
                  <span role="columnheader">Invoice</span>
                </div>

                <div
                  v-for="payment in payments"
                  :key="payment.id"
                  :class="[historyColumns, 'border-b border-back-secondary px-6 py-4 text-sm text-white last:border-b-0']"
                  role="row"
                >
                  <span role="cell" class="font-medium">{{ payment.date }}</span>
                  <span role="cell" class="text-secondary/80">{{ payment.description }}</span>
                  <span role="cell" class="tabular-nums">{{ payment.amount }}</span>
                  <span role="cell">
                    <span :class="['inline-flex rounded-full px-3 py-1 text-xs font-semibold', statusClasses[payment.status]]">
                      {{ payment.status }}
                    </span>
                  </span>
                  <span role="cell">
                    <button
                      type="button"
                      class="font-semibold text-brand-green hover:underline disabled:opacity-50"
                      :disabled="viewingOrder !== ''"
                      @click="viewInvoice(payment)"
                    >
                      {{ viewingOrder === payment.orderId ? 'Opening...' : 'View' }}
                    </button>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- Downgrade confirmation -->
      <BaseModal :model-value="downgradeOpen" label="Confirm downgrade" @update:model-value="closeDowngrade">
        <div class="rounded-t-3xl border border-back-secondary bg-back-prime p-6 text-white sm:p-8 md:rounded-3xl">
          <h2 class="text-2xl font-extrabold">Downgrade to {{ downgradePlan?.name }}?</h2>
          <p class="mt-3 text-sm leading-relaxed text-secondary/80">
            You are on {{ tierLabel(user.tier) }}. The change takes effect right away and your daily listening
            limit becomes the {{ downgradePlan?.name }} limit. Payments you already made are not refunded.
          </p>

          <p
            v-if="downgradeError"
            class="mt-5 rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-sm font-medium text-red-300"
            role="alert"
          >
            {{ downgradeError }}
          </p>

          <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <BaseButton variant="outlineLight" :disabled="isDowngrading" @click="closeDowngrade">Keep my plan</BaseButton>
            <BaseButton
              class="!bg-brand-green !bg-none !text-back-prime !shadow-none"
              :disabled="isDowngrading"
              @click="confirmDowngrade(refresh)"
            >
              {{ isDowngrading ? 'Downgrading...' : 'Yes, downgrade' }}
            </BaseButton>
          </div>
        </div>
      </BaseModal>
    </template>
  </AppLayout>
</template>
