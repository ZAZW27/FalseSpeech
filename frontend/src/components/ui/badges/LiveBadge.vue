<script setup>
defineProps({
    label: {type: String, required: true},
});
</script>

<template>
    <span
        class="inline-flex items-center gap-2.5 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-[13px] font-medium text-white/90 backdrop-blur"
    >
        <span
            class="size-2.5 rounded-full bg-[#B7D894] shadow-[0_0_12px_rgba(224, 248, 199,1)]"
        />
        {{ label }}
    </span>
</template>
