<script setup>
import BaseButton from "@/components/ui/buttons/BaseButton.vue";
import PlanTag from "@/components/ui/badges/PlanTag.vue";
import Icon from "@/components/ui/icons/Icon.vue";

defineProps({
    plan: {type: Object, required: true},
});
</script>

<template>
    <!--
    - border + -mt-px/-ml-px: full grey border on every card; neighbours overlap
      by 1px so shared edges stay a single line
    - plan-card: hooks the animated lime border (see <style> below)
  -->
    <article
        :class="[
            'plan-card relative -ml-px -mt-px flex flex-col border border-zinc-300 px-8 py-12',
            'transition-all duration-300 ease-out',
            'hover:z-20 hover:scale-[1.06] hover:shadow-[0_24px_60px_rgba(32,39,52,0.3)]',
            'lg:min-h-[640px]',
            'lg:[&:hover+*]:translate-x-4 lg:[&:has(+_*:hover)]:-translate-x-4',
            plan.featured
                ? 'bg-gradient-to-br from-back-prime via-back-secondary to-[#2f6b5e] text-white'
                : 'bg-white text-back-prime',
        ]"
    >
        <div class="flex items-center gap-3">
            <h3 class="text-2xl font-bold">{{ plan.name }}</h3>
            <PlanTag v-if="plan.tag" :label="plan.tag" />
        </div>

        <!-- @container: the price scales with the card's own width, so it never overflows -->
        <div class="mt-8 @container">
            <p
                class="whitespace-nowrap font-extrabold leading-tight text-[length:clamp(1.75rem,14cqw,3rem)]"
            >
                {{ plan.price }}
            </p>
            <p
                :class="[
                    'mt-1 text-sm',
                    plan.featured ? 'text-muted' : 'text-back-prime/60',
                ]"
            >
                {{ plan.period }}
            </p>
        </div>

        <hr
            :class="[
                'my-8 border-t',
                plan.featured ? 'border-white/15' : 'border-back-prime/10',
            ]"
        />

        <ul class="flex flex-1 flex-col gap-4">
            <li
                v-for="feature in plan.features"
                :key="feature"
                class="flex items-center gap-3 text-[15px]"
            >
                <span
                    :class="[
                        'flex size-[22px] shrink-0 items-center justify-center rounded-full',
                        plan.featured
                            ? 'bg-brand-green/25 text-brand-green'
                            : 'bg-back-prime/10 text-back-prime',
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
            class="mt-10"
        >
            {{ plan.cta.label }}
        </BaseButton>
    </article>
</template>

<!-- Not scoped: @property must be global -->
<style>
@property --border-angle {
    syntax: "<angle>";
    inherits: false;
    initial-value: 0deg;
}

.plan-card::after {
    content: "";
    position: absolute;
    inset: -1px; /* sits exactly on top of the grey border */
    padding: 2px; /* thickness of the lime line */
    pointer-events: none;
    background: conic-gradient(
        from var(--border-angle),
        transparent 0%,
        transparent 55%,
        #a3e635 80%,
        #ecfccb 100%
    );
    /* cut out the middle so only the ring is visible */
    -webkit-mask:
        linear-gradient(#000 0 0) content-box,
        linear-gradient(#000 0 0);
    -webkit-mask-composite: xor;
    mask-composite: exclude;
    opacity: 0;
    transition: opacity 0.3s ease;
    animation: plan-border-spin 2.2s linear infinite;
}

.plan-card:hover::after {
    opacity: 1;
}

@keyframes plan-border-spin {
    to {
        --border-angle: 360deg;
    }
}
</style>
