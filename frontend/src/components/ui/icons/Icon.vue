<script setup>
import {computed} from "vue";
import dashUrl from "./dash.svg";
import historyUrl from "./history.svg";
import planUrl from "./plan.svg";
import playUrl from "./play.svg";
import logoUrl from "./icon.svg";

// Needs the Font Awesome 6 stylesheet once in index.html:
// <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css" />
const props = defineProps({
    name: {type: String, required: true},
    size: {type: [Number, String], default: 20},
});

// 1) Own SVG files. Drawn as a mask, so they follow the text color (text-white, text-brand-green, ...).
const svgIcons = {
    dashboard: dashUrl,
    history: historyUrl,
    card: planUrl,
    plan: planUrl,
    play: playUrl,
    logo: logoUrl,
    waveform: logoUrl, // old name, kept so older usages still show the app icon
};

// 2) Font Awesome 6 (solid) from the CDN.
const faIcons = {
    shield: "fa-shield-halved",
    menu: "fa-bars",
    check: "fa-check",
    user: "fa-user",
    profile: "fa-user",
    trend: "fa-arrow-trend-up",
    search: "fa-magnifying-glass",
    close: "fa-xmark",
    "chevron-right": "fa-chevron-right",
    alert: "fa-triangle-exclamation",
    stop: "fa-stop",
    logout: "fa-right-from-bracket",
};

const svgUrl = computed(() => svgIcons[props.name]);
const faClass = computed(() => faIcons[props.name]);

const box = computed(() => ({width: `${props.size}px`, height: `${props.size}px`}));
const maskStyle = computed(() => ({
    ...box.value,
    backgroundColor: "currentColor",
    maskImage: `url("${svgUrl.value}")`,
    WebkitMaskImage: `url("${svgUrl.value}")`,
    maskRepeat: "no-repeat",
    WebkitMaskRepeat: "no-repeat",
    maskPosition: "center",
    WebkitMaskPosition: "center",
    maskSize: "contain",
    WebkitMaskSize: "contain",
}));
</script>

<template>
    <!-- Own SVG -->
    <span
        v-if="svgUrl"
        class="inline-block shrink-0"
        :style="maskStyle"
        :data-icon="name"
        aria-hidden="true"
    />

    <!-- Font Awesome 6 -->
    <i
        v-else-if="faClass"
        :class="['fa-solid', faClass, 'inline-flex shrink-0 items-center justify-center leading-none']"
        :style="{...box, fontSize: `${Math.round(size * 0.85)}px`}"
        :data-icon="name"
        aria-hidden="true"
    />

    <!-- Unknown name: the "@" placeholder -->
    <span
        v-else
        class="inline-flex shrink-0 items-center justify-center font-bold leading-none"
        :style="{...box, fontSize: `${Math.round(size * 0.8)}px`}"
        :data-icon="name"
        :title="`icon: ${name}`"
        aria-hidden="true"
        >@</span
    >
</template>
