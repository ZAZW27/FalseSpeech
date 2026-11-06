<script setup>
import {computed} from "vue";
import Icon from "@/components/ui/icons/Icon.vue";

const props = defineProps({
    size: {
        type: String,
        default: "lg",
        validator: v => ["sm", "md", "lg", "xl"].includes(v),
    },
    // playing swaps the play icon for a stop icon.
    playing: {type: Boolean, default: false},
    // Pulsing outer ring. On by default (landing hero), dashboard ties it to playing.
    pulse: {type: Boolean, default: true},
    label: {type: String, default: "Start listening"},
});

defineEmits(["click"]);

const sizes = {
    sm: {
        wrap: "size-[104px]",
        ring: "inset-[10%]",
        disc: "inset-[20%]",
        icon: 24,
        glow: "shadow-[0_0_28px_rgba(182,242,60,0.45)]",
    },
    md: {
        wrap: "size-[96px] md:size-[120px]",
        ring: "inset-[12px]",
        disc: "inset-[24px]",
        icon: 26,
        glow: "shadow-[0_0_32px_rgba(182,242,60,0.45)]",
    },
    lg: {
        wrap: "size-[94px] md:size-[122px] xl:size-[152px]",
        ring: "inset-[10%]",
        disc: "inset-[20%]",
        icon: 30,
        glow: "shadow-[0_0_32px_rgba(182,242,60,0.45)]",
    },
    xl: {
        wrap: "size-[200px] sm:size-[260px]",
        ring: "inset-[10%]",
        disc: "inset-[20%]",
        icon: 64,
        glow: "shadow-[0_0_90px_rgba(182,242,60,0.55)]",
    },
};

const s = computed(() => sizes[props.size]);
</script>

<template>
    <button
        type="button"
        :aria-label="label"
        :aria-pressed="playing"
        :class="['group relative shrink-0 rounded-full', s.wrap]"
        @click="$emit('click', $event)"
    >
        <span
            v-if="pulse"
            class="absolute inset-0 animate-pulse-ring rounded-full border border-lime-400/40"
        />
        <span
            class="absolute inset-0 rounded-full border border-lime-300/30 bg-lime-200/5"
        />
        <span
            :class="[
                'absolute rounded-full border border-lime-300/40 bg-lime-200/10',
                s.ring,
            ]"
        />
        <span
            :class="[
                'absolute flex items-center justify-center rounded-full bg-linear-to-br from-[#c0f38a] via-[#b6dd8c] to-[#d8ebc4] text-navy-900 transition group-hover:scale-105',
                s.disc,
                s.glow,
            ]"
        >
            <Icon :name="playing ? 'stop' : 'play'" :size="s.icon" />
        </span>
    </button>
</template>
