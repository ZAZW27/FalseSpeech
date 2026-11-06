<script setup>
import AppLayout from "@/components/layout/AppLayout.vue";
import FreeListener from "@/components/dashboard/FreeListener.vue";
import PaidDashboard from "@/components/dashboard/PaidDashboard.vue";

const greeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
};
</script>

<template>
    <AppLayout>
        <template #topbar="{user}">
            <h1 class="text-3xl font-extrabold tracking-tight lg:text-[32px]">
                Dashboard
            </h1>
            <p class="mt-1.5 text-sm text-muted">
                {{ greeting() }}, {{ user.name }}. Here's how your listening is
                going.
            </p>
        </template>

        <template #default="{user, updateQuota}">
            <FreeListener
                v-if="user.tier === 'free'"
                :user="user"
                :update-quota="updateQuota"
            />
            <PaidDashboard v-else :user="user" :update-quota="updateQuota" />
        </template>
    </AppLayout>
</template>
