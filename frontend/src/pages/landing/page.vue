<script setup>
import Hero from "@/pages/landing/hero.vue";
import About from "@/pages/landing/about.vue";
import Subscription from "@/pages/landing/subscription.vue";
import {useSectionScroll} from "@/assets/js/useSectionScroll";

useSectionScroll("section[id], footer[id]", {duration: 700});
</script>

<template>
    <Hero />
    <About />
    <Subscription />
</template>
