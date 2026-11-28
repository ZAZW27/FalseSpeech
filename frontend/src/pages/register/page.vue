<script setup>
import {computed, onBeforeUnmount, ref} from "vue";
import {RouterLink, useRouter} from "vue-router";
import AuthLayout from "@/components/layout/AuthLayout.vue";
import BrandPanel from "@/pages/login/BrandPanel.vue";
import FormField from "@/components/ui/inputs/FormField.vue";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import Icon from "@/components/ui/icons/Icon.vue";

const API_BASE = (import.meta.env.VITE_API_URL || "https://falsespeech.putrahomelab.com").replace(/\/+$/, "");
const SEND_OTP_URL = `${API_BASE}/api/auth/register/send-otp`;
const VERIFY_OTP_URL = `${API_BASE}/api/auth/register/verify-otp`;
const REDIRECT_DELAY_MS = 1500;

const router = useRouter();

const name = ref("");
const email = ref("");
const phone = ref("");
const password = ref("");

const otpCode = ref("");
const isOtpSent = ref(false);

const isLoading = ref(false);
const isResending = ref(false);
const resendCooldown = ref(0);
const otpExpiresIn = ref(0);
const errorMessage = ref("");
const successMessage = ref("");

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
let redirectTimer = null;
let cooldownTimer = null;
let expiryTimer = null;

const formattedOtpExpiry = computed(() => {
    const mins = Math.floor(otpExpiresIn.value / 60);
    const secs = otpExpiresIn.value % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
});

const startOtpExpiryTimer = (seconds = 300) => {
    clearInterval(expiryTimer);
    otpExpiresIn.value = seconds;
    expiryTimer = setInterval(() => {
        if (otpExpiresIn.value <= 1) {
            clearInterval(expiryTimer);
            otpExpiresIn.value = 0;
        } else {
            otpExpiresIn.value -= 1;
        }
    }, 1000);
};

const startResendCooldown = (seconds = 60) => {
    clearInterval(cooldownTimer);
    resendCooldown.value = seconds;
    cooldownTimer = setInterval(() => {
        if (resendCooldown.value <= 1) {
            clearInterval(cooldownTimer);
            resendCooldown.value = 0;
        } else {
            resendCooldown.value -= 1;
        }
    }, 1000);
};

const handleOtpInput = e => {
    const cleanValue = e.target.value.replace(/[^0-9]/g, "");
    otpCode.value = cleanValue.slice(0, 6);
};

const readError = (data, status) => {
    if (status === 404) return "Koneksi ke server gagal (Not Found).";
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
        const messages = data.detail.map(item => item?.msg).filter(Boolean);
        if (messages.length) return messages.join(". ");
    }
    return "Terjadi kesalahan. Silakan coba lagi.";
};

const submitRegistration = async () => {
    if (isLoading.value) return;
    errorMessage.value = "";

    if (
        !name.value.trim() ||
        !email.value.trim() ||
        !phone.value.trim() ||
        !password.value
    ) {
        errorMessage.value = "Harap isi semua kolom.";
        return;
    }
    if (!emailPattern.test(email.value.trim())) {
        errorMessage.value = "Harap masukkan format email yang valid.";
        return;
    }

    isLoading.value = true;

    try {
        const response = await fetch(SEND_OTP_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                name: name.value.trim(),
                email: email.value.trim(),
                phone: phone.value.trim(),
                password: password.value,
            }),
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            errorMessage.value = readError(data, response.status);
            return;
        }

        isOtpSent.value = true;
        startResendCooldown(60);
        startOtpExpiryTimer(300);
        successMessage.value =
            "Kode OTP telah dikirim ke email Anda. Cek inbox/spam.";
    } catch (err) {
        errorMessage.value = "Tidak dapat terhubung ke server.";
    } finally {
        isLoading.value = false;
    }
};

const resendOtp = async () => {
    if (isResending.value || resendCooldown.value > 0) return;
    errorMessage.value = "";
    successMessage.value = "";
    isResending.value = true;

    try {
        const response = await fetch(SEND_OTP_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                name: name.value.trim(),
                email: email.value.trim(),
                phone: phone.value.trim(),
                password: password.value,
            }),
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            errorMessage.value = readError(data, response.status);
            return;
        }

        otpCode.value = "";
        startResendCooldown(60);
        startOtpExpiryTimer(300);
        successMessage.value =
            data?.message ||
            "Kode OTP baru telah dikirim ulang ke email Anda. Cek inbox/spam.";
    } catch (err) {
        errorMessage.value = "Tidak dapat terhubung ke server.";
    } finally {
        isResending.value = false;
    }
};

const submitOtp = async () => {
    if (isLoading.value) return;
    errorMessage.value = "";

    if (!otpCode.value || otpCode.value.length !== 6) {
        errorMessage.value = "Kode OTP harus 6 digit angka.";
        return;
    }

    isLoading.value = true;
    successMessage.value = "";

    try {
        const response = await fetch(VERIFY_OTP_URL, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                email: email.value.trim(),
                otp_code: otpCode.value.trim(),
            }),
        });

        const data = await response.json().catch(() => null);

        if (!response.ok) {
            errorMessage.value = readError(data, response.status);
            return;
        }

        successMessage.value = "Registrasi berhasil! Silakan login.";
        redirectTimer = setTimeout(
            () => router.push("/login"),
            REDIRECT_DELAY_MS,
        );
    } catch (err) {
        errorMessage.value = "Tidak dapat terhubung ke server.";
    } finally {
        isLoading.value = false;
    }
};

onBeforeUnmount(() => {
    clearTimeout(redirectTimer);
    clearInterval(cooldownTimer);
    clearInterval(expiryTimer);
});
</script>

<template>
    <AuthLayout>
        <template #brand>
            <BrandPanel
                title="Create your account."
                subtitle="Join False Speech on the Free plan and run your first voice check in minutes."
            />
        </template>

        <div
            class="rounded-[28px] border border-back-prime/10 bg-white p-6 shadow-[0_20px_60px_rgba(7,20,51,0.08)] sm:p-[45px]"
        >
            <p
                class="text-xs font-semibold uppercase tracking-[0.2em] text-brand-green"
            >
                {{ isOtpSent ? "Verification" : "Get started" }}
            </p>
            <h1
                class="mt-2.5 text-[28px] font-extrabold leading-tight text-back-prime sm:text-[32px]"
            >
                {{ isOtpSent ? "Enter OTP Code" : "Sign up for False Speech" }}
            </h1>
            <p class="mt-3 text-sm text-back-prime/70">
                {{
                    isOtpSent
                        ? `We sent a 6-digit code to ${email}`
                        : "New accounts start on the Free plan."
                }}
            </p>

            <!-- TAHAP 1: FORM REGISTRASI -->
            <form
                v-if="!isOtpSent"
                class="mt-8 flex flex-col gap-5"
                novalidate
                @submit.prevent="submitRegistration"
            >
                <FormField
                    id="register-name"
                    v-model="name"
                    tone="light"
                    label="Full Name"
                    placeholder="Your full name"
                    autocomplete="name"
                />
                <FormField
                    id="register-email"
                    v-model="email"
                    tone="light"
                    type="email"
                    label="Email"
                    placeholder="you@example.com"
                    autocomplete="email"
                />
                <FormField
                    id="register-phone"
                    v-model="phone"
                    tone="light"
                    type="tel"
                    label="Phone Number"
                    placeholder="0811122233"
                    autocomplete="tel"
                />
                <FormField
                    id="register-password"
                    v-model="password"
                    tone="light"
                    type="password"
                    label="Password"
                    placeholder="Create a password"
                    autocomplete="new-password"
                />

                <p
                    v-if="errorMessage"
                    class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
                    role="alert"
                >
                    {{ errorMessage }}
                </p>

                <BaseButton
                    type="submit"
                    variant="dark"
                    size="lg"
                    block
                    class="!h-[54px]"
                    :disabled="isLoading"
                >
                    {{ isLoading ? "Processing..." : "Create account" }}
                </BaseButton>
            </form>

            <!-- TAHAP 2: FORM OTP -->
            <form
                v-else
                class="mt-8 flex flex-col gap-5"
                novalidate
                @submit.prevent="submitOtp"
            >
                <div class="flex flex-col gap-2">
                    <div class="flex items-center justify-between gap-2">
                        <label
                            for="register-otp"
                            class="text-sm font-semibold text-back-prime"
                            >6-Digit OTP Code</label
                        >
                        <span
                            :class="[
                                'rounded-full px-2.5 py-0.5 tabular-nums text-xs font-semibold',
                                otpExpiresIn === 0
                                    ? 'bg-red-100 text-red-600'
                                    : otpExpiresIn <= 60
                                      ? 'bg-amber-100 text-amber-700'
                                      : 'bg-slate-100 text-slate-600',
                            ]"
                        >
                            {{
                                otpExpiresIn > 0
                                    ? `Expires in ${formattedOtpExpiry}`
                                    : "OTP expired"
                            }}
                        </span>
                    </div>
                    <input
                        id="register-otp"
                        :value="otpCode"
                        @input="handleOtpInput"
                        type="text"
                        inputmode="numeric"
                        placeholder="123456"
                        maxlength="6"
                        class="rounded-xl border border-back-prime/20 bg-white px-4 py-3 text-base text-back-prime focus:border-brand-green focus:outline-none focus:ring-2 focus:ring-brand-green/20"
                    />
                    <p
                        v-if="otpExpiresIn === 0"
                        class="text-xs font-medium text-red-500"
                    >
                        This code has expired. Click <strong>Resend OTP</strong> below to request a new code.
                    </p>
                </div>

                <p
                    v-if="errorMessage"
                    class="rounded-xl border border-red-400/30 bg-red-400/10 px-4 py-3 text-sm text-red-400"
                    role="alert"
                >
                    {{ errorMessage }}
                </p>
                <p
                    v-if="successMessage"
                    class="rounded-xl border border-brand-green/30 bg-brand-green/10 px-4 py-3 text-sm font-medium text-back-prime"
                    role="status"
                >
                    {{ successMessage }}
                </p>

                <!-- BUTTON LOGIC FIXED: DISABLED KALAU OTP KURANG DARI 6 DIGIT ATAU EXPIRED -->
                <BaseButton
                    type="submit"
                    variant="dark"
                    size="lg"
                    block
                    class="!h-[54px]"
                    :disabled="isLoading || otpCode.length !== 6 || otpExpiresIn === 0"
                >
                    {{ isLoading ? "Verifying..." : "Verify OTP" }}
                </BaseButton>

                <div class="mt-1 flex items-center justify-between gap-3 text-sm">
                    <button
                        type="button"
                        class="font-semibold text-blue-600 transition hover:underline disabled:cursor-not-allowed disabled:text-gray-400 disabled:no-underline"
                        :disabled="isResending || resendCooldown > 0"
                        @click="resendOtp"
                    >
                        {{
                            isResending
                                ? "Sending new OTP..."
                                : resendCooldown > 0
                                  ? `Resend OTP (${resendCooldown}s)`
                                  : "Resend OTP"
                        }}
                    </button>

                    <button
                        type="button"
                        class="text-gray-500 transition hover:text-gray-800"
                        @click="
                            isOtpSent = false;
                            errorMessage = '';
                            successMessage = '';
                            otpCode = '';
                            resendCooldown = 0;
                        "
                    >
                        Wrong email? Go back.
                    </button>
                </div>
            </form>

            <p
                v-if="!isOtpSent"
                class="mt-6 text-center text-sm text-back-prime/70"
            >
                Already have an account?
                <RouterLink
                    to="/login"
                    class="font-semibold text-blue-600 hover:underline"
                    >Login here</RouterLink
                >
            </p>

            <p
                class="mt-6 flex items-center justify-center gap-2 text-center text-[13px] text-back-prime/60"
            >
                <span class="text-brand-green"
                    ><Icon name="shield" :size="16"
                /></span>
                Audio is processed in memory and never stored. Because we broke
                :(
            </p>
        </div>
    </AuthLayout>
</template>
