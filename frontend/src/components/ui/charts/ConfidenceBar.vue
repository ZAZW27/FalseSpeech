<script setup>
import {computed} from "vue";
import {getTone} from "@/assets/js/tone";

const props = defineProps({
    value: {type: Number, required: true},
    tone: {type: String, default: "success"},
    heightClass: {type: String, default: "h-2"},
});

const width = computed(() => `${Math.min(100, Math.max(0, props.value))}%`);
</script>

<template>
    <div
        :class="[
            'w-full overflow-hidden rounded-full bg-white/10',
            heightClass,
        ]"
        role="progressbar"
        :aria-valuenow="value"
        aria-valuemin="0"
        aria-valuemax="100"
    >
        <div
            :class="[
                'h-full rounded-full transition-all duration-500',
                getTone(tone).bar,
            ]"
            :style="{width}"
        />
    </div>
</template>
