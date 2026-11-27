<script setup>
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";
import {authFetch, clearToken} from "@/assets/js/api";
import {getInitials} from "@/assets/js/format";
import AppLayout from "@/components/layout/AppLayout.vue";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import FormField from "@/components/ui/inputs/FormField.vue";
import Icon from "@/components/ui/icons/Icon.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import PageSkeleton from "@/components/ui/skeletons/PageSkeleton.vue";
import LogoutConfirmPopover from "@/components/ui/modals/LogoutConfirmPopover.vue";

const TIER_LABELS = {
    free: "Free",
    pro: "Pro",
    pro_max: "Pro Max",
    lifetime: "Lifetime",
};

const router = useRouter();

const user = ref(null);
const isLoading = ref(true);
const isSaving = ref(false);
const isLoggingOut = ref(false);
const successMessage = ref("");
const errorMessage = ref("");

// Change password state (RF-02)
const pwForm = ref({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
});
const isChangingPassword = ref(false);
const pwSuccessMessage = ref("");
const pwErrorMessage = ref("");

const changePassword = async () => {
    if (isChangingPassword.value) return;
    pwSuccessMessage.value = "";
    pwErrorMessage.value = "";

    if (!pwForm.value.currentPassword) {
        pwErrorMessage.value = "Current password is required.";
        return;
    }
    if (pwForm.value.newPassword.length < 8) {
        pwErrorMessage.value = "New password must be at least 8 characters.";
        return;
    }
    if (pwForm.value.newPassword !== pwForm.value.confirmPassword) {
        pwErrorMessage.value = "New password and confirmation do not match.";
        return;
    }

    isChangingPassword.value = true;
    try {
        const response = await authFetch("/api/users/change-password", {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                current_password: pwForm.value.currentPassword,
                new_password: pwForm.value.newPassword,
            }),
        });
        if (response.status === 401) {
            handleUnauthorized();
            return;
        }
        if (!response.ok) {
            pwErrorMessage.value = await readError(
                response,
                "Could not update your password. Please try again.",
            );
            return;
        }
        pwForm.value = { currentPassword: "", newPassword: "", confirmPassword: "" };
        pwSuccessMessage.value = "Your password has been updated.";
    } catch {
        pwErrorMessage.value = "Could not reach the server. Please try again.";
    } finally {
        isChangingPassword.value = false;
    }
};

// Editable copy of the profile. The server value stays in `user`.
const form = ref({name: "", phone: ""});

const initials = computed(() => getInitials(user.value?.name ?? "") || "?");
const tierLabel = computed(() => {
    const tier = user.value?.tier ?? "";
    return (
        TIER_LABELS[tier] ??
        tier.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase())
    );
});

const hasChanges = computed(() => {
    if (!user.value) return false;
    return (
        form.value.name.trim() !== user.value.name ||
        form.value.phone.trim() !== user.value.phone
    );
});

const syncForm = data => {
    form.value = {name: data.name ?? "", phone: data.phone ?? ""};
};

const handleUnauthorized = () => {
    clearToken();
    router.replace("/login");
};

// Backend errors can be a string or a list of validation items.
const readError = async (response, fallback) => {
    try {
        const body = await response.json();
        if (typeof body?.detail === "string") return body.detail;
        if (Array.isArray(body?.detail) && body.detail[0]?.msg)
            return body.detail[0].msg;
    } catch {
        // Body was not JSON, use the fallback.
    }
    return fallback;
};

const loadUser = async () => {
    isLoading.value = true;
    errorMessage.value = "";

    try {
        const response = await authFetch("/api/users/me");

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }
        if (!response.ok)
            throw new Error(`Request failed with status ${response.status}`);

        const data = await response.json();
        user.value = data;
        syncForm(data);
    } catch {
        errorMessage.value = "Could not load your profile. Please try again.";
    } finally {
        isLoading.value = false;
    }
};

const saveChanges = async () => {
    if (isSaving.value || !user.value) return;

    successMessage.value = "";
    errorMessage.value = "";

    const name = form.value.name.trim();
    const phone = form.value.phone.trim();

    if (!name) {
        errorMessage.value = "Full name cannot be empty.";
        return;
    }
    if (!phone) {
        errorMessage.value = "Phone number cannot be empty.";
        return;
    }

    isSaving.value = true;

    try {
        const response = await authFetch("/api/users/me", {
            method: "PATCH",
            body: JSON.stringify({name, phone}),
        });

        if (response.status === 401) {
            handleUnauthorized();
            return;
        }
        if (!response.ok) {
            errorMessage.value = await readError(
                response,
                "Could not save your changes. Please try again.",
            );
            return;
        }

        const updated = await response.json();
        user.value = updated;
        syncForm(updated);
        successMessage.value = "Your profile has been updated.";
    } catch {
        errorMessage.value = "Could not reach the server. Please try again.";
    } finally {
        isSaving.value = false;
    }
};

const logoutConfirmOpen = ref(false);

const askLogout = () => {
    logoutConfirmOpen.value = !logoutConfirmOpen.value;
};

const logout = async () => {
    if (isLoggingOut.value) return;
    isLoggingOut.value = true;
    logoutConfirmOpen.value = false;

    // Tokens are stateless, so the server call is best effort only.
    try {
        await authFetch("/api/auth/logout", {method: "POST"});
    } catch {
        // Ignore network errors, the local token is cleared either way.
    }

    clearToken();
    router.replace("/login");
};

onMounted(loadUser);
</script>

<template>
    <AppLayout
        title="Profile Settings"
        subtitle="Manage your personal information."
    >
        <!-- Loading -->
        <PageSkeleton v-if="isLoading" variant="profile" :show-header="false" />

        <!-- Load error -->
        <div
            v-else-if="!user"
            class="rounded-3xl border-2 border-danger/30 bg-danger/10 p-8 text-center"
            role="alert"
        >
            <p class="text-danger">
                {{
                    errorMessage ||
                    "Could not load your profile. Please try again."
                }}
            </p>
            <BaseButton class="mt-5" @click="loadUser">Try again</BaseButton>
        </div>

        <div
            v-else
            class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)]"
        >
            <!-- Left column: read-only summary -->
            <section
                class="flex flex-col items-center rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-8 text-center"
                aria-label="Account summary"
            >
                <div
                    class="flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-back-secondary to-brand-green text-3xl font-bold tracking-wide text-slate-100 shadow-inner"
                    aria-hidden="true"
                >
                    {{ initials }}
                </div>

                <h2 class="mt-5 max-w-full truncate text-xl font-bold text-slate-100">
                    {{ user.name }}
                </h2>
                <p class="mt-1 max-w-full truncate text-sm text-slate-400">
                    {{ user.email }}
                </p>

                <dl
                    class="mt-6 w-full rounded-2xl border-2 border-back-secondary bg-back-prime/60 px-5 py-4 text-left"
                >
                    <div class="flex items-center justify-between gap-2">
                        <dt class="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                            Current Plan
                        </dt>
                        <PlanTag label="ACTIVE" />
                    </div>
                    <dd class="mt-1.5 text-lg font-bold text-slate-100">
                        {{ tierLabel }}
                    </dd>
                </dl>

                <div class="relative mt-6 w-full">
                    <BaseButton
                        class="w-full inline-flex items-center justify-center gap-2"
                        variant="outlineLight"
                        :disabled="isLoggingOut"
                        :aria-expanded="logoutConfirmOpen"
                        @click="askLogout"
                    >
                        <Icon name="logout" :size="15" />
                        {{ isLoggingOut ? "Logging out..." : "Log out" }}
                    </BaseButton>

                    <LogoutConfirmPopover
                        :open="logoutConfirmOpen"
                        :busy="isLoggingOut"
                        position-class="top-full left-0 right-0 mt-2"
                        @cancel="logoutConfirmOpen = false"
                        @confirm="logout"
                    />
                </div>
            </section>

            <!-- Right column: editable form -->
            <section
                class="rounded-3xl border-2 border-back-secondary bg-back-secondary/40 p-8"
                aria-label="Edit profile"
            >
                <h2 class="text-lg font-bold text-slate-100">Personal Information</h2>
                <p class="mt-1 text-sm text-slate-400">
                    Update your name and phone number. Your email cannot be
                    changed.
                </p>

                <form
                    class="mt-6 flex flex-col gap-5"
                    novalidate
                    @submit.prevent="saveChanges"
                >
                    <FormField
                        id="profile-name"
                        v-model="form.name"
                        label="Full Name"
                        type="text"
                        placeholder="Your full name"
                        autocomplete="name"
                    />

                    <FormField
                        id="profile-phone"
                        v-model="form.phone"
                        label="Phone Number"
                        type="tel"
                        placeholder="Your phone number"
                        autocomplete="tel"
                    />

                    <FormField
                        id="profile-email"
                        :model-value="user.email"
                        label="Email"
                        type="email"
                        disabled
                        readonly
                    />

                    <p
                        v-if="successMessage"
                        class="rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-slate-100"
                        role="status"
                    >
                        {{ successMessage }}
                    </p>

                    <p
                        v-if="errorMessage"
                        class="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
                        role="alert"
                    >
                        {{ errorMessage }}
                    </p>

                    <div class="flex justify-end">
                        <BaseButton
                            class="w-full sm:w-auto"
                            :disabled="isSaving || !hasChanges"
                            @click="saveChanges"
                        >
                            {{ isSaving ? "Saving..." : "Save Changes" }}
                        </BaseButton>
                    </div>
                </form>

                <!-- Change Password (RF-02) -->
                <div class="mt-10 border-t border-white/10 pt-8">
                    <h2 class="text-lg font-bold text-slate-100">Change Password</h2>
                    <p class="mt-1 text-sm text-slate-400">
                        Update your account password. Must be at least 8 characters.
                    </p>

                    <form
                        class="mt-6 flex flex-col gap-5"
                        novalidate
                        @submit.prevent="changePassword"
                    >
                        <FormField
                            id="profile-current-password"
                            v-model="pwForm.currentPassword"
                            label="Current Password"
                            type="password"
                            placeholder="Enter current password"
                            autocomplete="current-password"
                        />

                        <FormField
                            id="profile-new-password"
                            v-model="pwForm.newPassword"
                            label="New Password"
                            type="password"
                            placeholder="At least 8 characters"
                            autocomplete="new-password"
                        />

                        <FormField
                            id="profile-confirm-password"
                            v-model="pwForm.confirmPassword"
                            label="Confirm New Password"
                            type="password"
                            placeholder="Re-enter new password"
                            autocomplete="new-password"
                        />

                        <p
                            v-if="pwSuccessMessage"
                            class="rounded-xl border border-white/15 bg-white/10 px-4 py-3 text-sm font-medium text-slate-100"
                            role="status"
                        >
                            {{ pwSuccessMessage }}
                        </p>

                        <p
                            v-if="pwErrorMessage"
                            class="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger"
                            role="alert"
                        >
                            {{ pwErrorMessage }}
                        </p>

                        <div class="flex justify-end">
                            <BaseButton
                                class="w-full sm:w-auto"
                                :disabled="isChangingPassword"
                                @click="changePassword"
                            >
                                {{ isChangingPassword ? "Updating..." : "Update Password" }}
                            </BaseButton>
                        </div>
                    </form>
                </div>
            </section>
        </div>
    </AppLayout>
</template>
