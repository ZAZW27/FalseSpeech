<script setup>
defineProps({
    label: {type: String, required: true},
});
</script>

<template>
    <span
        class="inline-flex items-center rounded-full bg-lime-400 px-2.5 py-1 text-[11px] font-bold leading-none text-back-prime"
    >
        {{ label }}
    </span>
</template>
