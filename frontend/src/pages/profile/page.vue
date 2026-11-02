<script setup>
import {computed, onMounted, ref} from "vue";
import {useRouter} from "vue-router";
import {authFetch, clearToken} from "@/assets/js/api";
import {getInitials} from "@/assets/js/format";
import AppLayout from "@/components/layout/AppLayout.vue";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import FormField from "@/components/ui/inputs/FormField.vue";

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

const logout = async () => {
    if (isLoggingOut.value) return;
    isLoggingOut.value = true;

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
        <p
            v-if="isLoading"
            class="py-16 text-center text-sm text-muted"
            role="status"
        >
            Loading profile...
        </p>

        <!-- Load error -->
        <div
            v-else-if="!user"
            class="rounded-3xl border border-danger/30 bg-danger/10 p-8 text-center"
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
                class="flex flex-col items-center rounded-3xl border border-white/10 bg-white/[0.04] p-8 text-center"
                aria-label="Account summary"
            >
                <div
                    class="flex h-24 w-24 items-center justify-center rounded-full border border-lime-400/40 bg-lime-400/10 text-3xl font-bold tracking-wide text-lime-400"
                    aria-hidden="true"
                >
                    {{ initials }}
                </div>

                <h2 class="mt-5 max-w-full truncate text-xl font-semibold">
                    {{ user.name }}
                </h2>
                <p class="mt-1 max-w-full truncate text-sm text-muted">
                    {{ user.email }}
                </p>

                <dl
                    class="mt-6 w-full rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-left"
                >
                    <dt
                        class="text-[11px] font-semibold uppercase tracking-wider text-muted"
                    >
                        Current Tier
                    </dt>
                    <dd class="mt-1 text-lg font-semibold text-lime-400">
                        {{ tierLabel }}
                    </dd>
                </dl>

                <BaseButton
                    class="mt-6 w-full"
                    variant="outlineLight"
                    :disabled="isLoggingOut"
                    @click="logout"
                >
                    {{ isLoggingOut ? "Logging out..." : "Log out" }}
                </BaseButton>
            </section>

            <!-- Right column: editable form -->
            <section
                class="rounded-3xl border border-white/10 bg-white/[0.04] p-8"
                aria-label="Edit profile"
            >
                <h2 class="text-lg font-semibold">Personal Information</h2>
                <p class="mt-1 text-sm text-muted">
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
                        class="rounded-xl border border-lime-400/30 bg-lime-400/10 px-4 py-3 text-sm font-medium text-lime-400"
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
            </section>
        </div>
    </AppLayout>
</template>
