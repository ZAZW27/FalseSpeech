<script setup>
import {computed, ref} from "vue";
import {useRoute} from "vue-router";
import {getPlanById} from "@/assets/data/plans";
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import PlanModal from "@/components/ui/modals/PlanModal.vue";
import Icon from "@/components/ui/icons/Icon.vue";

const route = useRoute();
// Re-evaluates when the :id param changes.
const plan = computed(() => getPlanById(route.params.id));

const modalOpen = ref(false);
</script>

<template>
    <section
        class="relative min-h-svh overflow-hidden bg-[#1d2739] pb-16 pt-32 md:pb-24 md:pt-40 lg:pb-[130px]"
    >
        <div
            class="pointer-events-none absolute inset-0 bg-[linear-gradient(-30deg,transparent_5%,rgba(220,200,250,0.10)_50%,transparent_95%)]"
        ></div>

        <div
            class="relative mx-auto w-full max-w-[1440px] px-6 lg:px-12 xl:px-20"
        >
            <BaseButton
                to="/subscription"
                variant="ghost"
                size="sm"
                class="mb-8 !px-0"
            >
                Back to plans
            </BaseButton>

            <div v-if="plan" class="grid gap-12 lg:grid-cols-2 lg:gap-20">
                <div>
                    <div class="flex items-center gap-3">
                        <h1 class="text-4xl font-extrabold md:text-5xl">
                            {{ plan.name }}
                        </h1>
                        <PlanTag v-if="plan.tag" :label="plan.tag" />
                    </div>
                    <p
                        class="mt-6 bg-linear-to-br from-brand-green to-secondary bg-clip-text text-4xl font-extrabold text-transparent"
                    >
                        {{ plan.price }}
                    </p>
                    <p class="mt-1 text-sm text-muted">{{ plan.period }}</p>
                    <p
                        class="mt-8 max-w-[540px] text-base leading-relaxed text-muted"
                    >
                        {{ plan.description }}
                    </p>
                </div>

                <div
                    class="border border-white/10 bg-white/[0.04] p-8 backdrop-blur md:p-10"
                >
                    <h2 class="text-xl font-bold">What is included</h2>
                    <ul class="mt-6 flex flex-col gap-4">
                        <li
                            v-for="feature in plan.features"
                            :key="feature"
                            class="flex items-center gap-3 text-[15px]"
                        >
                            <span
                                class="flex size-[22px] shrink-0 items-center justify-center rounded-full bg-brand-green/20 text-brand-green"
                            >
                                <Icon name="check" :size="14" />
                            </span>
                            {{ feature }}
                        </li>
                    </ul>

                    <!-- Interactive feature #2: opens the confirmation modal -->
                    <BaseButton
                        size="lg"
                        block
                        class="mt-8"
                        @click="modalOpen = true"
                    >
                        {{ plan.cta.label }}
                    </BaseButton>
                </div>

                <PlanModal v-model="modalOpen" :plan="plan" />
            </div>

            <div v-else class="max-w-[480px]" role="alert">
                <h1 class="text-3xl font-extrabold">Plan not found</h1>
                <p class="mt-4 text-muted">
                    There is no plan with the id "{{ route.params.id }}".
                </p>
                <BaseButton to="/subscription" class="mt-8"
                    >View all plans</BaseButton
                >
            </div>
        </div>
    </section>
</template>
