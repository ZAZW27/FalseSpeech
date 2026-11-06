<script setup>
import {about, features} from "@/assets/data/features";
import SectionHeader from "@/components/ui/sections/SectionHeader.vue";
import FeatureCard from "@/components/ui/cards/FeatureCard.vue";
</script>

<template>
    <section
        id="about"
        class="relative snap-start overflow-hidden bg-[#202734] min-h-svh py-16 md:py-24 lg:py-[130px]"
    >
        <div
            class="pointer-events-none absolute inset-0 bg-[linear-gradient(-35deg,transparent_0%,rgba(255,216,255,0.1)_50%,transparent_100%)]"
        ></div>

        <div
            class="relative mx-auto w-full max-w-[1440px] px-6 lg:px-12 xl:px-20"
        >
            <SectionHeader
                align="split"
                :eyebrow="about.eyebrow"
                :title="about.title"
                :description="about.description"
            />

            <div class="mt-12 grid lg:mt-[72px] lg:grid-cols-3">
                <FeatureCard
                    v-for="feature in features"
                    :key="feature.id"
                    :number="feature.number"
                    :title="feature.title"
                    :description="feature.description"
                />
            </div>
        </div>
    </section>
</template>
