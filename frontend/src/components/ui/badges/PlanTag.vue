<script setup>
defineProps({
    label: {type: String, required: true},
});
</script>

<template>
    <span
        class="inline-flex items-center rounded-full border border-brand-green/50 bg-[#2f6b5e] px-2.5 py-1 text-[11px] font-bold leading-none text-white"
    >
        {{ label }}
    </span>
</template>

