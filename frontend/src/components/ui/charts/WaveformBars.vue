<script setup>
import {computed, ref} from "vue";

const props = defineProps({
    count: {type: Number, default: 48},
    barClass: {
        type: String,
        default: "bg-gradient-to-b from-emerald-100 to-lime-300",
    },
    barWidthClass: {type: String, default: "w-1 md:w-2"},
    wobbles: {type: Boolean, default: false},
    glow: {type: Boolean, default: false},
    animated: {type: Boolean, default: false},
    pullStrength: {type: Number, default: 0.6},
    pullReach: {type: Number, default: 3},
});

const bars = computed(() =>
    Array.from({length: props.count}, (_, i) => {
        const raw = Math.abs(
            Math.sin(i * 0.42) * 0.6 + Math.sin(i * 0.17 + 1) * 0.4,
        );
        return Math.max(0.12, Math.min(1, raw));
    }),
);

const pointerIndex = ref(null);

const onMove = event => {
    if (!props.wobbles) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const ratio = (event.clientX - rect.left) / rect.width;
    pointerIndex.value = Math.min(1, Math.max(0, ratio)) * (props.count - 1);
};

const onLeave = () => {
    pointerIndex.value = null;
};

const scaleFor = i => {
    if (pointerIndex.value === null) return 1;
    const d = i - pointerIndex.value;
    const falloff = Math.exp(
        -(d * d) / (2 * props.pullReach * props.pullReach),
    );
    return 1 - props.pullStrength * falloff;
};
</script>

<template>
    <div
        class="flex h-full w-full items-center justify-between"
        aria-hidden="true"
        @pointermove="onMove"
        @pointerleave="onLeave"
    >
        <span
            v-for="(height, i) in bars"
            :key="i"
            :class="[
                'relative origin-center rounded-full transition-transform duration-200 ease-out',
                barWidthClass,
                barClass,
                glow
                    ? 'drop-shadow-[0_0_20px_rgba(255,255,255,0.35)] shadow-[inset_1px_2px_5px_rgba(0,0,0,0.8)]'
                    : '',
                animated ? 'animate-wave' : '',
            ]"
            :style="{
                height: `${height * 100}%`,
                transform: `scaleY(${scaleFor(i)})`,
                animationDelay: animated ? `${i * 45}ms` : undefined,
            }"
        />
    </div>
</template>
