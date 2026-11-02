<script setup>
import {hero} from "@/assets/data/hero";
import {heroResults} from "@/assets/data/heroResults";
import {useListeningSession} from "@/assets/js/useListeningSession";
import LiveBadge from "@/components/ui/badges/LiveBadge.vue";
import PlayButton from "@/components/ui/buttons/PlayButton.vue";
import AnalysisCard from "@/components/ui/cards/AnalysisCard.vue";
import WaveformBars from "@/components/ui/charts/WaveformBars.vue";

const {start} = useListeningSession();

// Desktop placement for each result card (data-driven, index matches heroResults).
const cardPositions = [
    "lg:absolute lg:right-12 lg:top-[136px] lg:w-[320px] xl:right-[25px]",
    "lg:absolute lg:right-[274px] lg:top-[620px] lg:w-[332px] xl:right-[274px]",
];
</script>

<template>
    <section
        id="home"
        class="relative isolate overflow-hidden bg-gradient-to-br from-[#040B1F] via-[#071433] to-[#0B2A6B]"
    >
        <!-- Background depth layers -->
        <span
            class="pointer-events-none absolute md:-left-67 md:-top-67 -left-40 -top-40 -z-10 size-[320px] rounded-full bg-[#1b5bff]/40 blur-[120px] lg:size-[620px]"
        />
        <span
            class="pointer-events-none absolute -bottom-32 -right-32 -z-10 size-[350px] rounded-full bg-lime-400/40 blur-[130px] lg:size-[640px]"
        />
        <span
            class="pointer-events-none absolute left-0 top-32 -z-10 select-none text-[200px] font-extrabold uppercase leading-[0.85] tracking-tighter text-white/[0.04] lg:text-[300px] xl:text-[360px]"
            aria-hidden="true"
        >
            False<br />Speech
        </span>

        <div
            class="relative mx-auto flex w-full max-w-480 flex-col px-6 pb-16 pt-[104px] lg:min-h-[900px] lg:px-12 lg:pt-[200px] xl:px-20"
        >
            <!-- Foreground copy -->
            <div class="max-w-[660px]">
                <LiveBadge :label="hero.badge" />

                <h1
                    class="mt-7 text-balance text-4xl font-extrabold leading-[1.08] tracking-tight md:text-6xl xl:text-[68px]"
                >
                    {{ hero.headlineLead
                    }}<span class="text-lime-300">{{
                        hero.headlineHighlight
                    }}</span>
                </h1>

                <p
                    class="mt-7 max-w-[540px] text-base leading-relaxed text-muted md:text-lg"
                >
                    {{ hero.subtext }}
                </p>

                <div class="mt-10 flex items-center gap-5">
                    <PlayButton @click="start" />
                    <div>
                        <p class="text-xl font-bold md:text-2xl">
                            {{ hero.cta.label }}
                        </p>
                        <p class="mt-1.5 text-sm text-muted">
                            {{ hero.cta.caption }}
                        </p>
                    </div>
                </div>
            </div>

            <!-- Waveform -->
            <div
                class="mt-12 h-[118px] w-full max-w-[348px] md:h-[160px] md:max-w-[520px] lg:absolute lg:right-0 lg:top-[340px] lg:mt-0 lg:h-[235px] lg:w-[620px] lg:max-w-none xl:w-[696px]"
            >
                <WaveformBars
                    :count="44"
                    glow
                    wobbles
                    bar-width-class="w-1 lg:w-2"
                />
            </div>

            <!-- Analysis cards -->
            <div
                class="mt-8 flex flex-col gap-5 md:flex-row md:flex-wrap lg:mt-0 lg:block"
            >
                <AnalysisCard
                    v-for="(result, i) in heroResults"
                    :key="result.id"
                    :result="result"
                    :class="['md:flex-1 lg:flex-none', cardPositions[i]]"
                />
            </div>
        </div>
    </section>
</template>
