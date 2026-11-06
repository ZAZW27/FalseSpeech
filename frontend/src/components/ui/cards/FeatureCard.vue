<script setup>
defineProps({
    number: {type: String, required: true},
    title: {type: String, required: true},
    description: {type: String, required: true},
});
</script>

<template>
    <article
        class="-mt-px border-y border-white/20 p-8 transition-colors duration-300 hover:bg-white/[0.04] hover:backdrop-blur-lg lg:border-l lg:[&:nth-child(3n+1)]:border-l-0"
    >
        <span
            class="flex size-12 items-center justify-start rounded-xl text-4xl font-bold text-white"
        >
            {{ number }}
        </span>
        <h3 class="mt-8 text-2xl font-bold">{{ title }}</h3>
        <p class="mt-5 text-[15px] leading-relaxed text-muted">
            {{ description }}
        </p>
    </article>
</template>
