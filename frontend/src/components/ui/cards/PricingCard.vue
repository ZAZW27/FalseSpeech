<script setup>
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import Icon from "@/components/ui/icons/Icon.vue";

defineProps({
    plan: {type: Object, required: true},
});
</script>

<template>
    <article
        :class="[
            'flex flex-col rounded-3xl border p-8 hover:-translate-y-4 hover:shadow hover:shadow-emerald-500 transition-all duration-200 ease-out',
            plan.featured
                ? 'border-transparent bg-gradient-to-br from-[#0B1F4D] via-[#12306F] to-[#0F6E7A] text-white shadow-[0_24px_60px_rgba(11,31,77,0.35)]'
                : 'border-navy-900/10 bg-white text-navy-900 shadow-[0_8px_20px_rgba(7,20,51,0.1)]',
        ]"
    >
        <div class="flex items-center gap-3">
            <h3 class="text-2xl font-bold">{{ plan.name }}</h3>
            <PlanTag v-if="plan.tag" :label="plan.tag" />
        </div>

        <div class="mt-6">
            <p class="text-[34px] font-extrabold leading-tight md:text-4xl">
                {{ plan.price }}
            </p>
            <p
                :class="[
                    'mt-1 text-sm',
                    plan.featured ? 'text-muted' : 'text-navy-900/60',
                ]"
            >
                {{ plan.period }}
            </p>
        </div>

        <hr
            :class="[
                'my-6 border-t',
                plan.featured ? 'border-white/15' : 'border-navy-900/10',
            ]"
        />

        <ul class="flex flex-1 flex-col gap-3.5">
            <li
                v-for="feature in plan.features"
                :key="feature"
                class="flex items-center gap-3 text-[15px]"
            >
                <span
                    :class="[
                        'flex size-[22px] shrink-0 items-center justify-center rounded-full text-brand-green',
                        plan.featured
                            ? 'bg-brand-green/25'
                            : 'bg-brand-green/15',
                    ]"
                >
                    <Icon name="check" :size="14" />
                </span>
                {{ feature }}
            </li>
        </ul>

        <!-- The CTA opens the dynamic route /detail/:id -->
        <BaseButton
            :to="{name: 'detail', params: {id: plan.id}}"
            :variant="plan.cta.variant"
            size="lg"
            block
            class="mt-8"
        >
            {{ plan.cta.label }}
        </BaseButton>
    </article>
</template>
