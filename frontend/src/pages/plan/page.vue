<script setup>
import {ref, onMounted} from "vue";
import {useRouter} from "vue-router";
import {plans} from "@/assets/data/plans";
import {authFetch, clearToken} from "@/assets/js/api";
import {formatDuration, toPercent} from "@/assets/js/format";
import AppLayout from "@/components/layout/AppLayout.vue";
import PricingCard from "@/components/ui/cards/PricingCard.vue";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";

const router = useRouter();

const TIER_RANK = {free: 0, pro: 1, pro_max: 2, lifetime: 3};

const toTier = planId => planId.replace("-", "_");

const upgradingTier = ref("");
const errorMessage = ref("");
const noticeMessage = ref("");

const paymentHistory = ref([]);
const isLoadingHistory = ref(true);

const tierLabel = tier =>
    plans.find(plan => toTier(plan.id) === tier)?.name ?? tier;

const actionFor = (user, plan) => {
    const tier = toTier(plan.id);
    if (tier === user.tier)
        return {label: "Current Plan", disabled: true, isUpgrade: false};
    const isUpgrade = (TIER_RANK[tier] ?? 0) > (TIER_RANK[user.tier] ?? 0);
    return {
        label: isUpgrade ? "Upgrade" : "Downgrade",
        disabled: false,
        isUpgrade,
    };
};

const upgrade = async targetTier => {
    errorMessage.value = "";
    noticeMessage.value = "";
    upgradingTier.value = targetTier;

    try {
        const response = await authFetch("/api/subscription/upgrade", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({target_tier: targetTier}),
        });

        if (response.status === 401) {
            clearToken();
            router.replace("/login");
            return;
        }
        if (!response.ok) {
            const body = await response.json().catch(() => ({}));
            throw new Error(
                typeof body.detail === "string"
                    ? body.detail
                    : `Request failed with status ${response.status}`,
            );
        }

        const data = await response.json();
        if (!data.payment_url)
            throw new Error("Payment link was not returned by the server.");
        window.location.href = data.payment_url;
    } catch (error) {
        errorMessage.value = `Could not start the payment. ${error.message}`;
        upgradingTier.value = "";
    }
};

const handleAction = (plan, action) => {
    if (action.isUpgrade) {
        upgrade(toTier(plan.id));
        return;
    }
    errorMessage.value = "";
    noticeMessage.value =
        "Plan downgrades are not available online yet. Please contact support to change your plan.";
};

const fetchBillingHistory = async () => {
    isLoadingHistory.value = true;
    try {
        const response = await authFetch("/api/billing/history");

        if (response.status === 401) {
            clearToken();
            router.replace("/login");
            return;
        }

        if (response.ok) {
            const data = await response.json();

            paymentHistory.value = data.map(item => {
                const tierName =
                    item.tier === "pro_max"
                        ? "Pro Max"
                        : item.tier.charAt(0).toUpperCase() +
                          item.tier.slice(1);
                const billingType =
                    item.tier === "lifetime" ? "one-time" : "monthly";

                return {
                    id: item.invoice_id,
                    date: new Date(item.issued_at).toLocaleDateString("en-US", {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                    }),
                    description: `${tierName} - ${billingType}`,
                    amount: `Rp${item.amount_idr.toLocaleString("id-ID")}`,
                    status: item.status === "success" ? "Paid" : "Pending",
                };
            });
        }
    } catch (error) {
        console.error("Failed to fetch billing history:", error);
    } finally {
        isLoadingHistory.value = false;
    }
};

onMounted(() => {
    fetchBillingHistory();
});

const statusClasses = {
    Paid: "bg-brand-green/15 text-brand-green",
    Pending: "bg-secondary/10 text-secondary",
    Failed: "bg-red-400/15 text-red-300",
};

const historyColumns =
    "grid grid-cols-[1.2fr_2fr_1.2fr_1fr_1fr] items-center gap-4";
</script>

<template>
    <AppLayout
        title="Plan & Billing"
        subtitle="Manage your subscription and review your usage."
    >
        <template #default="{user}">
            <div
                class="flex flex-col gap-8 rounded-3xl bg-back-prime p-5 md:p-8"
            >
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
                    <section
                        class="rounded-3xl border border-back-secondary bg-back-secondary/40 p-6"
                    >
                        <p
                            class="text-[11px] font-semibold uppercase tracking-wider text-secondary/70"
                        >
                            Current plan
                        </p>
                        <h2 class="mt-2 text-3xl font-extrabold text-white">
                            {{ tierLabel(user.tier) }}
                        </h2>
                    </section>

                    <!-- Usage -->
                    <section
                        class="rounded-3xl border border-back-secondary bg-back-secondary/40 p-6"
                    >
                        <p
                            class="text-[11px] font-semibold uppercase tracking-wider text-secondary/70"
                        >
                            Usage
                        </p>

                        <p
                            v-if="user.tier === 'lifetime'"
                            class="mt-3 text-3xl font-extrabold uppercase tracking-wide text-brand-green"
                        >
                            UNLIMITED POWER
                        </p>

                        <div v-else class="mt-3">
                            <p
                                class="text-sm font-semibold tabular-nums text-white"
                            >
                                {{ formatDuration(user.quota_used) }} of
                                {{ formatDuration(user.quota_limit) }} used
                            </p>
                            <div
                                class="mt-3 h-2.5 w-full overflow-hidden rounded-full bg-back-prime"
                                role="progressbar"
                                aria-label="Daily quota used"
                                aria-valuemin="0"
                                aria-valuemax="100"
                                :aria-valuenow="
                                    toPercent(user.quota_used, user.quota_limit)
                                "
                            >
                                <div
                                    class="h-full rounded-full bg-brand-green transition-all"
                                    :style="{
                                        width: `${toPercent(user.quota_used, user.quota_limit)}%`,
                                    }"
                                />
                            </div>
                            <p class="mt-2 text-xs text-secondary/70">
                                {{
                                    toPercent(
                                        user.quota_used,
                                        user.quota_limit,
                                    )
                                }}% of your quota
                            </p>
                        </div>
                    </section>
                </div>

                <section>
                    <h2 class="text-xl font-bold text-white">Compare plans</h2>

                    <div
                        class="mt-5 grid pl-px pt-px md:grid-cols-2 xl:grid-cols-4"
                    >
                        <PricingCard
                            v-for="plan in plans"
                            :key="plan.id"
                            :plan="plan"
                            dark
                        >
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
                                    :disabled="
                                        actionFor(user, plan).disabled ||
                                        upgradingTier !== ''
                                    "
                                    @click="
                                        handleAction(
                                            plan,
                                            actionFor(user, plan),
                                        )
                                    "
                                >
                                    {{
                                        upgradingTier === toTier(plan.id)
                                            ? "Redirecting..."
                                            : actionFor(user, plan).label
                                    }}
                                </BaseButton>
                            </template>
                        </PricingCard>
                    </div>
                </section>

                <!-- Payment history -->
                <section>
                    <h2 class="text-xl font-bold text-white">
                        Payment history
                    </h2>

                    <div class="mt-5 rounded-3xl border border-back-secondary">
                        <div class="overflow-x-auto">
                            <div
                                class="min-w-[640px]"
                                role="table"
                                aria-label="Payment history"
                            >
                                <div
                                    :class="[
                                        historyColumns,
                                        'border-b border-back-secondary px-6 py-4 text-[11px] font-semibold uppercase tracking-wider text-secondary/70',
                                    ]"
                                    role="row"
                                >
                                    <span role="columnheader">Date</span>
                                    <span role="columnheader">Description</span>
                                    <span role="columnheader">Amount</span>
                                    <span role="columnheader">Status</span>
                                    <span role="columnheader">Invoice</span>
                                </div>

                                <div
                                    v-if="isLoadingHistory"
                                    class="px-6 py-8 text-center text-sm text-secondary"
                                >
                                    Loading payment history...
                                </div>

                                <div
                                    v-else-if="paymentHistory.length === 0"
                                    class="px-6 py-8 text-center text-sm text-secondary"
                                >
                                    No payment history found. Upgrade your plan
                                    to see invoices here.
                                </div>

                                <!-- Billing history -->
                                <div
                                    v-else
                                    v-for="payment in paymentHistory"
                                    :key="payment.id"
                                    :class="[
                                        historyColumns,
                                        'border-b border-back-secondary px-6 py-4 text-sm text-white last:border-b-0',
                                    ]"
                                    role="row"
                                >
                                    <span role="cell" class="font-medium">{{
                                        payment.date
                                    }}</span>
                                    <span
                                        role="cell"
                                        class="text-secondary/80"
                                        >{{ payment.description }}</span
                                    >
                                    <span role="cell" class="tabular-nums">{{
                                        payment.amount
                                    }}</span>
                                    <span role="cell">
                                        <span
                                            :class="[
                                                'inline-flex rounded-full px-3 py-1 text-xs font-semibold',
                                                statusClasses[payment.status] ||
                                                    statusClasses.Pending,
                                            ]"
                                        >
                                            {{ payment.status }}
                                        </span>
                                    </span>
                                    <span role="cell">
                                        <a
                                            href="#"
                                            class="font-semibold text-brand-green hover:underline"
                                            @click.prevent
                                            >View</a
                                        >
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </template>
    </AppLayout>
</template>
