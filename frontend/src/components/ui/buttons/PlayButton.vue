<script setup>
import {computed} from "vue";
import Icon from "@/components/ui/icons/Icon.vue";

const props = defineProps({
    size: {
        type: String,
        default: "lg",
        validator: v => ["md", "lg"].includes(v),
    },
    label: {type: String, default: "Start listening"},
});

defineEmits(["click"]);

const sizes = {
    md: {
        wrap: "size-[96px] md:size-[120px]",
        outer: "",
        ring: "inset-[12px]",
        disc: "inset-[24px]",
        icon: 26,
    },
    lg: {
        wrap: "size-[94px] md:size-[122px] xl:size-[152px]",
        outer: "",
        ring: "inset-[10%]",
        disc: "inset-[20%]",
        icon: 30,
    },
};

const s = computed(() => sizes[props.size]);
</script>

<template>
    <button
        type="button"
        :aria-label="label"
        :class="['group relative shrink-0 rounded-full', s.wrap]"
        @click="$emit('click', $event)"
    >
        <span
            class="absolute inset-0 animate-pulse-ring rounded-full border border-lime-400/40"
        />
        <span
            class="absolute inset-0 rounded-full border border-lime-400/30 bg-lime-400/5"
        />
        <span
            :class="[
                'absolute rounded-full border border-lime-400/40 bg-lime-400/10',
                s.ring,
            ]"
        />
        <span
            :class="[
                'absolute flex items-center justify-center rounded-full bg-gradient-to-br from-lime-300  to-emerald-500 text-navy-900 shadow-[0_0_32px_rgba(182,242,60,0.45)] transition group-hover:scale-105',
                s.disc,
            ]"
        >
            <Icon name="play" :size="s.icon" />
        </span>
    </button>
</template>
