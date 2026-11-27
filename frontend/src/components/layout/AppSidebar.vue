<script setup>
import {computed, ref} from "vue";
import {RouterLink, useRouter} from "vue-router";
import {brand} from "@/assets/data/site";
import {appLinks} from "@/assets/data/appNavigation";
import {
    capitalize,
    formatDuration,
    getInitials,
    toPercent,
} from "@/assets/js/format";
import Icon from "@/components/ui/icons/Icon.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import ConfidenceBar from "@/components/ui/charts/ConfidenceBar.vue";
import LogoutConfirmPopover from "@/components/ui/modals/LogoutConfirmPopover.vue";

const ANDROID_APK_URL =
    import.meta.env.VITE_ANDROID_APK_URL || "/downloads/FalseSpeech.apk";
const ANDROID_DEEP_LINK = "falsespeech://open";
const ANDROID_TIERS = new Set(["pro_max", "lifetime"]);

const props = defineProps({
    // { name, tier, quota_used, quota_limit } from GET /api/users/me. Null while loading.
    user: {type: Object, default: null},
});

// "navigate" lets the mobile drawer close itself after a link is clicked.
const emit = defineEmits(["navigate", "logout"]);
const router = useRouter();

const logoutMenuOpen = ref(false);
const canUseAndroidApp = computed(() =>
    ANDROID_TIERS.has(String(props.user?.tier ?? "").toLowerCase()),
);
const isAndroidDevice = () =>
    typeof navigator !== "undefined" &&
    /android/i.test(navigator.userAgent || "");

const handleAndroidAppClick = () => {
    emit("navigate");
    if (!canUseAndroidApp.value) {
        router.push("/plan");
        return;
    }

    // On Android browser: try opening the installed app via deep link first.
    // If the app is not installed (tab stays visible), fall back to direct APK download.
    if (isAndroidDevice()) {
        let appOpened = false;
        const onVisibility = () => {
            if (document.hidden) appOpened = true;
        };
        document.addEventListener("visibilitychange", onVisibility, {
            once: true,
        });
        window.location.href = ANDROID_DEEP_LINK;
        setTimeout(() => {
            document.removeEventListener("visibilitychange", onVisibility);
            if (!appOpened && !document.hidden) {
                window.location.href = ANDROID_APK_URL;
            }
        }, 1200);
        return;
    }

    // Desktop browser: direct APK download
    const link = document.createElement("a");
    link.href = ANDROID_APK_URL;
    link.download = "FalseSpeech.apk";
    link.rel = "noopener noreferrer";
    document.body.appendChild(link);
    link.click();
    link.remove();
};

const toggleLogoutMenu = () => {
    logoutMenuOpen.value = !logoutMenuOpen.value;
};

const confirmLogout = () => {
    logoutMenuOpen.value = false;
    emit("logout");
};

const TIER_LABELS = {
    free: "Free",
    pro: "Pro",
    pro_max: "Pro Max",
    lifetime: "Lifetime",
};
const planLabel = computed(() => {
    const raw = String(props.user?.tier ?? "");
    const formatted = TIER_LABELS[raw] ?? capitalize(raw.replace(/_/g, " "));
    return `${formatted} plan`;
});
const balanceLabel = computed(
    () =>
        `Rp${new Intl.NumberFormat("id-ID").format(Number(props.user?.balance) || 0)}`,
);
const usedLabel = computed(() => formatDuration(props.user?.quota_used));
const limitLabel = computed(() => formatDuration(props.user?.quota_limit));
const percent = computed(() =>
    toPercent(props.user?.quota_used, props.user?.quota_limit),
);
</script>

<template>
    <div class="flex h-full flex-col px-5 py-8">
        <RouterLink
            to="/"
            class="flex items-center gap-2.5 px-2 text-xl font-bold text-white"
            @click="$emit('navigate')"
        >
            <Icon name="logo" :size="32" />
            {{ brand.name }}
        </RouterLink>

        <nav class="mt-8 flex flex-col gap-1.5" aria-label="App navigation">
            <RouterLink
                v-for="link in appLinks"
                :key="link.to"
                :to="link.to"
                class="flex h-12 items-center gap-3 rounded-xl border border-transparent px-4 text-[15px] font-medium text-secondary/70 transition hover:bg-white/5 hover:text-white"
                active-class="!border-brand-green/40 !bg-white/5 !text-white"
                @click="$emit('navigate')"
            >
                <Icon :name="link.icon" :size="20" />
                {{ link.label }}
            </RouterLink>
        </nav>

        <div class="mt-auto flex flex-col gap-5 pt-8">
            <!-- Android App Download Card (Mobile app icon + brief desc + main green button) -->
            <div
                class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 p-4 text-center"
            >
                <div
                    class="mx-auto flex size-11 items-center justify-center rounded-xl border border-brand-green/40 bg-back-prime shadow-inner"
                >
                    <svg
                        viewBox="0 0 64 64"
                        class="size-9"
                        fill="none"
                        aria-hidden="true"
                    >
                        <rect width="64" height="64" rx="14" fill="#202734" />
                        <g transform="translate(10 10) scale(1.375)">
                            <path
                                d="M7 14C7 12.8954 6.10457 12 5 12C3.89543 12 3 12.8954 3 14V18C3 19.1046 3.89543 20 5 20C6.10457 20 7 19.1046 7 18V14Z"
                                fill="#B7D894"
                            />
                            <path
                                d="M14 8C14 6.89543 13.1046 6 12 6C10.8954 6 10 6.89543 10 8V24C10 25.1046 10.8954 26 12 26C13.1046 26 14 25.1046 14 24V8Z"
                                fill="#B7D894"
                            />
                            <path
                                d="M21 11C21 9.89543 20.1046 9 19 9C17.8954 9 17 9.89543 17 11V21C17 22.1046 17.8954 23 19 23C20.1046 23 21 22.1046 21 21V11Z"
                                fill="#B7D894"
                            />
                            <path
                                d="M28 5C28 3.89543 27.1046 3 26 3C24.8954 3 24 3.89543 24 5V27C24 28.1046 24.8954 29 26 29C27.1046 29 28 28.1046 28 27V5Z"
                                fill="#B7D894"
                            />
                        </g>
                    </svg>
                </div>
                <p class="mt-2.5 text-xs font-bold text-slate-100">
                    False Speech Mobile
                </p>
                <p class="mt-1 text-[11px] leading-snug text-slate-400">
                    Check calls &amp; videos faster with our 1-tap Android
                    widget.
                </p>
                <button
                    type="button"
                    class="mt-3 flex w-full items-center justify-center gap-1.5 whitespace-nowrap rounded-xl bg-gradient-to-r from-[#b7d894] via-[#c3e2a2] to-[#a7cb82] px-2.5 py-2 text-[11px] font-bold text-back-prime shadow-sm transition hover:brightness-105"
                    @click="handleAndroidAppClick"
                >
                    <Icon name="download" :size="13" class="text-back-prime" />
                    <span class="font-bold text-back-prime">{{
                        canUseAndroidApp
                            ? "Download Android App"
                            : "Pro Max+ Required"
                    }}</span>
                </button>
            </div>

            <div
                v-if="user"
                class="rounded-2xl border-2 border-back-secondary bg-back-secondary/40 p-5"
            >
                <div class="flex items-center justify-between">
                    <span class="text-sm font-semibold text-white">{{
                        planLabel
                    }}</span>
                    <PlanTag label="ACTIVE" />
                </div>
                <div
                    class="mt-3 flex items-center justify-between border-b border-white/10 pb-3 text-xs"
                >
                    <span class="text-secondary/70">Balance</span>
                    <span class="font-bold text-brand-green">{{
                        balanceLabel
                    }}</span>
                </div>
                <div
                    class="mt-3 flex items-center justify-between text-xs text-secondary/70"
                >
                    <span>Today</span>
                    <span class="font-semibold text-white"
                        >{{ usedLabel }} / {{ limitLabel }}</span
                    >
                </div>
                <ConfidenceBar :value="percent" tone="lime" class="mt-3" />
            </div>

            <!-- Sidebar plan card skeleton while user loads -->
            <div
                v-else
                class="flex flex-col gap-3 rounded-2xl border-2 border-back-secondary bg-back-secondary/30 p-5"
            >
                <div class="flex items-center justify-between">
                    <div class="skeleton-shimmer h-4 w-24 rounded-md" />
                    <div class="skeleton-shimmer h-5 w-14 rounded-full" />
                </div>
                <div class="skeleton-shimmer h-3.5 w-full rounded-md" />
                <div class="skeleton-shimmer h-2.5 w-full rounded-full" />
            </div>

            <div class="relative">
                <LogoutConfirmPopover
                    :open="logoutMenuOpen"
                    position-class="bottom-full left-0 right-0 mb-2"
                    @cancel="logoutMenuOpen = false"
                    @confirm="confirmLogout"
                />

                <div v-if="user" class="flex items-center gap-3 px-1">
                    <RouterLink
                        to="/profile"
                        class="flex size-10 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-back-secondary to-brand-green text-sm font-bold text-white"
                        @click="$emit('navigate')"
                    >
                        {{ getInitials(user.name) }}
                    </RouterLink>
                    <div class="min-w-0">
                        <RouterLink
                            to="/profile"
                            class="block truncate text-sm font-semibold text-white hover:text-brand-green"
                            @click="$emit('navigate')"
                        >
                            {{ user.name }}
                        </RouterLink>
                        <button
                            type="button"
                            class="inline-flex items-center gap-1.5 text-xs text-secondary/70 transition hover:text-secondary"
                            :aria-expanded="logoutMenuOpen"
                            @click="toggleLogoutMenu"
                        >
                            <Icon name="logout" :size="12" />
                            Log out
                        </button>
                    </div>
                </div>

                <button
                    v-else
                    type="button"
                    class="flex h-11 w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 text-sm font-medium text-secondary/80 transition hover:bg-white/10 hover:text-white"
                    :aria-expanded="logoutMenuOpen"
                    @click="toggleLogoutMenu"
                >
                    <Icon name="logout" :size="14" />
                    Log out
                </button>
            </div>
        </div>
    </div>
</template>
