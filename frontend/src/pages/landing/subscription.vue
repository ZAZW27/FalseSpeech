<script setup>
import {pricingHeader, plans} from "@/assets/data/plans";
import SectionHeader from "@/components/ui/sections/SectionHeader.vue";
import PricingCard from "@/components/ui/cards/PricingCard.vue";
</script>

<template>
    <section
        id="subscription"
        class="snap-start min-h-svh bg-surface-light py-16 md:py-24 lg:py-[130px]"
    >
        <div class="mx-auto w-full max-w-[1440px] px-6 lg:px-12 xl:px-20">
            <SectionHeader
                align="center"
                tone="lilght"
                :eyebrow="pricingHeader.eyebrow"
                :title="pricingHeader.title"
                :description="pricingHeader.description"
            />

            <div
                class="mt-12 grid gap-5 md:grid-cols-2 lg:mt-16 xl:grid-cols-4 xl:gap-6"
            >
                <PricingCard
                    v-for="plan in plans"
                    :key="plan.id"
                    :plan="plan"
                />
            </div>
        </div>
    </section>
</template>
