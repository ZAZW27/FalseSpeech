<script setup>
import {useRouter} from "vue-router";
import {useAudioCapture} from "@/assets/js/useAudioCapture";
import PlayButton from "@/components/ui/buttons/PlayButton.vue";
import CaptureControls from "@/components/dashboard/CaptureControls.vue";
import VerdictDisplay from "@/components/dashboard/VerdictDisplay.vue";

// Scenario A: free users get the controls, the play button and the verdict only.
const props = defineProps({
    user: {type: Object, required: true},
    updateQuota: {type: Function, required: true},
});

const router = useRouter();

const {
    isListening,
    currentResult,
    devices,
    selectedDevice,
    mode,
    chunkSize,
    statusText,
    statusWarn,
    errorMessage,
    startCapture,
    stopCapture,
} = useAudioCapture({
    onQuota: props.updateQuota,
    onSessionExpired: () => router.replace("/login"),
});

const toggle = () => (isListening.value ? stopCapture() : startCapture());
</script>

<template>
    <div class="mx-auto flex max-w-[620px] flex-col items-center gap-10 py-6">
        <PlayButton
            size="xl"
            :playing="isListening"
            :pulse="isListening"
            :label="isListening ? 'Stop listening' : 'Start listening'"
            @click="toggle"
        />

        <VerdictDisplay
            :result="currentResult"
            :listening="isListening"
            :status-text="statusText"
            :status-warn="statusWarn"
            size="xl"
            :showProbs="false"
        />

        <p
            v-if="errorMessage"
            class="max-w-[420px] rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-center text-sm text-danger"
            role="alert"
        >
            {{ errorMessage }}
        </p>

        <section
            class="w-full rounded-3xl border border-white/10 bg-white/[0.04] p-6"
        >
            <CaptureControls
                v-model:mode="mode"
                v-model:selected-device="selectedDevice"
                v-model:chunk-size="chunkSize"
                :devices="devices"
                :locked="isListening"
            />
        </section>
    </div>
</template>
