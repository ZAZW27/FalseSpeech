<script setup>
import {about, features} from "@/assets/data/features";
import SectionHeader from "@/components/ui/sections/SectionHeader.vue";
import FeatureCard from "@/components/ui/cards/FeatureCard.vue";
</script>

<template>
    <section
        id="about"
        class="bg-[#202734] min-h-svh py-16 md:py-24 lg:py-[130px]"
    >
        <div class="mx-auto w-full max-w-[1440px] px-6 lg:px-12 xl:px-20">
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
