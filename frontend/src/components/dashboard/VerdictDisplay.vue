<script setup>
import {computed} from "vue";

const props = defineProps({
    result: {type: Object, default: null},
    listening: {type: Boolean, default: false},
    statusText: {type: String, default: ""},
    statusWarn: {type: Boolean, default: false},
    size: {
        type: String,
        default: "md",
        validator: v => ["md", "xl"].includes(v),
    },
    showProbs: {type: Boolean, default: true},
});

const toneClass = {
    real: "text-brand-green drop-shadow-[0_0_24px_rgba(22,199,132,0.45)]",
    fake: "text-danger drop-shadow-[0_0_24px_rgba(255,92,122,0.45)]",
    uncertain: "text-yellow-400 drop-shadow-[0_0_24px_rgba(250,204,21,0.35)]",
};

const label = computed(
    () => props.result?.label ?? (props.listening ? "..." : "-"),
);
const colorClass = computed(() =>
    props.result ? toneClass[props.result.tone] : "text-slate-500",
);

const probs = computed(() => {
    if (props.result) {
        return `fake ${(props.result.fake * 100).toFixed(1)}% / real ${(props.result.real * 100).toFixed(1)}%`;
    }
    return props.listening ? "capturing" : "Waiting for audio...";
});
</script>

<template>
    <div class="text-center" aria-live="polite">
        <p
            :class="[
                'font-extrabold tracking-wide',
                colorClass,
                size === 'xl' ? 'text-5xl sm:text-6xl' : 'text-4xl sm:text-5xl',
            ]"
        >
            {{ label }}
        </p>

        <p v-if="showProbs" class="mt-3 text-sm text-muted">
            {{ probs }}
        </p>

        <p
            v-if="statusText"
            :class="[
                'mt-2 font-mono text-xs',
                statusWarn ? 'font-semibold text-yellow-400' : 'text-slate-500',
            ]"
        >
            {{ statusText }}
        </p>
    </div>
</template>
