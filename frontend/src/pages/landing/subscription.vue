<script setup>
import {useRouter} from "vue-router";
import {pricingHeader, plans} from "@/assets/data/plans";
import {getToken} from "@/assets/js/api";
import SectionHeader from "@/components/ui/sections/SectionHeader.vue";
import PricingCard from "@/components/ui/cards/PricingCard.vue";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";

const router = useRouter();

const handlePlanClick = (plan) => {
    if (!getToken()) {
        router.push("/login");
        return;
    }
    router.push({name: "detail", params: {id: plan.id}});
};
</script>

<template>
    <section
        id="subscription"
        class="snap-start flex min-h-[100svh] flex-col justify-center bg-surface-light py-16 md:py-20 lg:py-24"
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
                >
                    <template #cta>
                        <BaseButton
                            :variant="plan.cta.variant"
                            size="lg"
                            block
                            class="mt-10"
                            @click="handlePlanClick(plan)"
                        >
                            {{ plan.cta.label }}
                        </BaseButton>
                    </template>
                </PricingCard>
            </div>
        </div>
    </section>
</template>
