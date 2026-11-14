<script setup>
import {computed} from "vue";
import {RouterLink, useRoute, useRouter} from "vue-router";
import {brand} from "@/assets/data/site";
import {navLinks} from "@/assets/data/navigation";
import {clearToken, getToken} from "@/assets/js/api";
import {useScrollPosition} from "@/assets/js/useScrollPosition";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import IconButton from "@/components/ui/buttons/IconButton.vue";
import Icon from "@/components/ui/icons/Icon.vue";

const emit = defineEmits(["open-menu"]);

const route = useRoute();
const router = useRouter();
const {isScrolled} = useScrollPosition();

// The detail page has no hero under the header, so it needs a solid header.
const solid = computed(() => isScrolled.value || route.name === "detail");

// The token lives in localStorage (not reactive), so it is read again on every navigation.
const isLoggedIn = computed(() => {
    void route.fullPath;
    return Boolean(getToken());
});

const logout = () => {
    clearToken();
    router.replace("/login");
};
</script>

<template>
    <header
        :class="[
            'fixed inset-x-0 top-0 z-40 transition-colors duration-300',
            solid
                ? 'bg-gradient-to-r from-back-prime via-back-prime to-back-secondary shadow-[0_8px_30px_rgba(0,0,0,0.3)]'
                : 'bg-transparent',
        ]"
    >
        <nav
            class="mx-auto flex h-[72px] w-full max-w-[1440px] items-center justify-between px-6 lg:h-20 lg:px-12 xl:px-20"
            aria-label="Main navigation"
        >
            <div class="flex items-center gap-10">
                <RouterLink
                    to="/"
                    class="flex items-center gap-2.5 text-lg font-bold text-white"
                >
                    <Icon name="logo" :size="28" />
                    {{ brand.name }}
                </RouterLink>

                <ul class="hidden items-center gap-8 lg:flex">
                    <li v-for="link in navLinks" :key="link.to">
                        <RouterLink
                            :to="link.to"
                            class="text-sm font-medium text-white/90 transition hover:text-brand-green"
                            active-class="!text-brand-green"
                            exact-active-class="!text-brand-green"
                        >
                            {{ link.label }}
                        </RouterLink>
                    </li>
                </ul>
            </div>

            <!-- Logged in: go to the app. Logged out: login and register. -->
            <div v-if="isLoggedIn" class="hidden items-center gap-5 lg:flex">
                <BaseButton to="/dashboard" size="sm"
                    ><Icon name="dashboard" :size="16" />Dashboard</BaseButton
                >
                <BaseButton size="sm" variant="outlineLight" @click="logout"
                    ><Icon name="logout" :size="14" />Log out</BaseButton
                >
            </div>
            <div v-else class="hidden items-center gap-5 lg:flex">
                <BaseButton to="/login" size="sm" variant="outlineLight"
                    >Login</BaseButton
                >
                <BaseButton to="/register" size="sm">Register</BaseButton>
            </div>

            <IconButton
                class="lg:hidden"
                icon="menu"
                label="Open menu"
                @click="emit('open-menu')"
            />
        </nav>
    </header>
</template>
