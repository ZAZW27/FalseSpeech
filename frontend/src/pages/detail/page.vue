<script setup>
import {computed, onMounted, ref} from "vue";
import {useRoute, useRouter} from "vue-router";
import {getPlanById} from "@/assets/data/plans";
import {authFetch, clearToken, getToken} from "@/assets/js/api";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import Icon from "@/components/ui/icons/Icon.vue";

const TIER_PRICE = {free: 0, pro: 49000, pro_max: 99000, lifetime: 2499000};
const TIER_RANK = {free: 0, pro: 1, pro_max: 2, lifetime: 3};

const route = useRoute();
const router = useRouter();

const plan = computed(() => getPlanById(route.params.id));
const targetTier = computed(() => (plan.value ? plan.value.id.replace("-", "_") : ""));
const targetPrice = computed(() => TIER_PRICE[targetTier.value] ?? 0);

const user = ref(null);
const isLoggedIn = computed(() => Boolean(getToken()));
const isProcessing = ref(false);
const errorMessage = ref("");
const successMessage = ref("");

const formatRupiah = amount =>
    `Rp${new Intl.NumberFormat("id-ID").format(Number(amount) || 0)}`;

const userBalance = computed(() => Number(user.value?.balance) || 0);
const currentPlanCredit = computed(() => {
    if (!user.value) return 0;
    const price = TIER_PRICE[user.value.tier] ?? 0;
    if (price <= 0) return 0;
    if (user.value.tier === "lifetime") return price;
    if (user.value.subscription_expires_at) {
        const expMs = new Date(user.value.subscription_expires_at).getTime();
        const remSecs = Math.max(0, (expMs - Date.now()) / 1000);
        const ratio = Math.min(1, remSecs / (30 * 86400));
        return Math.round(price * ratio);
    }
    return price;
});
const netAmountDue = computed(() =>
    Math.max(0, targetPrice.value - currentPlanCredit.value),
);
const isCurrentPlan = computed(() => user.value?.tier === targetTier.value);
const isUpgrade = computed(() => {
    if (!user.value) return true;
    return (TIER_RANK[targetTier.value] ?? 0) > (TIER_RANK[user.value.tier] ?? 0);
});
const canPayFullBalance = computed(
    () => netAmountDue.value === 0 || userBalance.value >= netAmountDue.value,
);
const canPayHybrid = computed(
    () =>
        netAmountDue.value > 0 &&
        userBalance.value > 0 &&
        userBalance.value < netAmountDue.value,
);
const remainingAfterBalance = computed(() =>
    Math.max(0, netAmountDue.value - userBalance.value),
);

const loadAccount = async () => {
    if (!getToken()) return;
    try {
        const res = await authFetch("/api/users/me");
        if (res.status === 401) {
            clearToken();
            user.value = null;
            return;
        }
        if (res.ok) user.value = await res.json();
    } catch {
        // Ignore network errors while viewing public plan details
    }
};

const checkout = async paymentMethod => {
    if (!getToken()) {
        router.push("/login");
        return;
    }
    if (isProcessing.value || !targetTier.value) return;

    errorMessage.value = "";
    successMessage.value = "";
    isProcessing.value = true;

    try {
        const res = await authFetch("/api/subscription/upgrade", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                target_tier: targetTier.value,
                payment_method: paymentMethod,
            }),
        });
        if (res.status === 401) {
            clearToken();
            router.push("/login");
            return;
        }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
            throw new Error(data?.detail || `Checkout failed (${res.status})`);
        }
        if (data.paid_with_balance) {
            successMessage.value = `Upgraded to ${plan.value.name} using your balance! Redirecting to Plan & Billing...`;
            await loadAccount();
            setTimeout(() => router.push("/plan"), 1200);
            return;
        }
        if (!data.payment_url) {
            throw new Error("Payment link was not returned by the server.");
        }
        window.location.href = data.payment_url;
    } catch (err) {
        errorMessage.value = err.message || "Could not process checkout.";
    } finally {
        isProcessing.value = false;
    }
};

onMounted(loadAccount);
</script>

<template>
    <section
        class="relative min-h-[100svh] overflow-hidden bg-[#1d2739] pb-16 pt-32 md:pb-24 md:pt-40 lg:pb-[130px]"
    >
        <div
            class="pointer-events-none absolute inset-0 bg-[linear-gradient(-30deg,transparent_5%,rgba(220,200,250,0.10)_50%,transparent_95%)]"
        ></div>

        <div
            class="relative mx-auto w-full max-w-[1440px] px-6 lg:px-12 xl:px-20"
        >
            <BaseButton
                :to="isLoggedIn ? '/plan' : '/subscription'"
                variant="ghost"
                size="sm"
                class="mb-8 !px-0"
            >
                Back to plans
            </BaseButton>

            <div v-if="plan" class="grid gap-12 lg:grid-cols-2 lg:gap-20">
                <div>
                    <div class="flex items-center gap-3">
                        <h1 class="text-4xl font-extrabold md:text-5xl">
                            {{ plan.name }}
                        </h1>
                        <PlanTag v-if="plan.tag" :label="plan.tag" />
                    </div>
                    <p
                        class="mt-6 bg-linear-to-br from-brand-green to-secondary bg-clip-text text-4xl font-extrabold text-transparent"
                    >
                        {{ plan.price }}
                    </p>
                    <p class="mt-1 text-sm text-muted">{{ plan.period }}</p>
                    <p
                        class="mt-8 max-w-[540px] text-base leading-relaxed text-muted"
                    >
                        {{ plan.description }}
                    </p>

                    <div
                        v-if="user"
                        class="mt-8 inline-flex items-center gap-4 rounded-2xl border-2 border-white/15 bg-white/[0.05] px-5 py-3.5 text-sm"
                    >
                        <span class="text-muted">Your Balance:</span>
                        <span class="text-base font-extrabold text-brand-green">
                            {{ formatRupiah(userBalance) }}
                        </span>
                    </div>
                </div>

                <div
                    class="rounded-3xl border-2 border-white/10 bg-white/[0.04] p-8 backdrop-blur md:p-10"
                >
                    <h2 class="text-xl font-bold">What is included</h2>
                    <ul class="mt-6 flex flex-col gap-4">
                        <li
                            v-for="feature in plan.features"
                            :key="feature"
                            class="flex items-center gap-3 text-[15px]"
                        >
                            <span
                                class="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-brand-green/20 text-brand-green"
                            >
                                <Icon name="check" :size="14" />
                            </span>
                            {{ feature }}
                        </li>
                    </ul>

                    <p
                        v-if="errorMessage"
                        class="mt-6 rounded-xl border border-red-400/40 bg-red-400/10 px-4 py-3 text-sm text-red-300"
                        role="alert"
                    >
                        {{ errorMessage }}
                    </p>
                    <p
                        v-if="successMessage"
                        class="mt-6 rounded-xl border border-brand-green/40 bg-brand-green/10 px-4 py-3 text-sm text-brand-green"
                        role="status"
                    >
                        {{ successMessage }}
                    </p>

                    <div class="mt-8 flex flex-col gap-3">
                        <BaseButton
                            v-if="!isLoggedIn"
                            size="lg"
                            block
                            @click="router.push('/login')"
                        >
                            Log in to Subscribe
                        </BaseButton>

                        <BaseButton
                            v-else-if="isCurrentPlan"
                            size="lg"
                            block
                            variant="outlineLight"
                            disabled
                        >
                            Current Plan
                        </BaseButton>

                        <BaseButton
                            v-else-if="!isUpgrade"
                            size="lg"
                            block
                            variant="outlineLight"
                            to="/plan"
                        >
                            Manage Downgrade in Plan &amp; Billing
                        </BaseButton>

                        <template v-else>
                            <div
                                v-if="currentPlanCredit > 0"
                                class="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-xs text-muted"
                            >
                                <div class="flex justify-between">
                                    <span>Plan price</span>
                                    <span>{{ formatRupiah(targetPrice) }}</span>
                                </div>
                                <div class="mt-1 flex justify-between text-brand-green">
                                    <span>Current plan credit</span>
                                    <span>-{{ formatRupiah(currentPlanCredit) }}</span>
                                </div>
                                <div class="mt-2 flex justify-between border-t border-white/10 pt-2 text-sm font-bold text-white">
                                    <span>Amount due</span>
                                    <span>{{ formatRupiah(netAmountDue) }}</span>
                                </div>
                            </div>

                            <BaseButton
                                v-if="canPayFullBalance"
                                size="lg"
                                block
                                :disabled="isProcessing"
                                @click="checkout('balance')"
                            >
                                {{
                                    isProcessing
                                        ? "Processing..."
                                        : `Pay with Balance (${formatRupiah(netAmountDue)})`
                                }}
                            </BaseButton>

                            <BaseButton
                                v-if="canPayHybrid"
                                size="lg"
                                block
                                :disabled="isProcessing"
                                @click="checkout('hybrid')"
                            >
                                {{
                                    isProcessing
                                        ? "Redirecting..."
                                        : `Use Balance + Pay ${formatRupiah(remainingAfterBalance)} via Midtrans`
                                }}
                            </BaseButton>

                            <BaseButton
                                v-if="netAmountDue > 0"
                                size="lg"
                                block
                                :variant="canPayFullBalance || canPayHybrid ? 'outlineLight' : 'primary'"
                                :disabled="isProcessing"
                                @click="checkout('midtrans')"
                            >
                                {{
                                    isProcessing
                                        ? "Redirecting..."
                                        : `Pay with Midtrans (${formatRupiah(netAmountDue)})`
                                }}
                            </BaseButton>
                        </template>
                    </div>
                </div>
            </div>

            <div v-else class="max-w-[480px]" role="alert">
                <h1 class="text-3xl font-extrabold">Plan not found</h1>
                <p class="mt-4 text-muted">
                    There is no plan with the id "{{ route.params.id }}".
                </p>
                <BaseButton to="/subscription" class="mt-8"
                    >View all plans</BaseButton
                >
            </div>
        </div>
    </section>
</template>
