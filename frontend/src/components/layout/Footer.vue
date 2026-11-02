<script setup>
import { brand } from '@/assets/data/site'
import SectionHeader from '@/components/ui/sections/SectionHeader.vue'
import ContactForm from '@/components/ui/forms/ContactForm.vue'
</script>

<template>
  <footer id="contact" class="border-t border-white/5 bg-navy-950">
    <div
      class="mx-auto flex w-full max-w-[1440px] flex-col gap-12 px-6 py-16 md:py-24 lg:flex-row lg:gap-20 lg:px-12 xl:px-20"
    >
      <div class="lg:w-1/3">
        <SectionHeader
          eyebrow="Contact"
          title="Questions about False Speech?"
          description="Send us a message and we will get back to you by email."
        />
      </div>

      <div class="lg:w-2/3">
        <ContactForm />
      </div>
    </div>

    <div class="border-t border-white/5">
      <div
        class="mx-auto flex w-full max-w-[1440px] flex-col gap-3 px-6 py-8 md:flex-row md:items-center md:justify-between lg:px-12 xl:px-20"
      >
        <p class="text-lg font-bold text-white">{{ brand.name }}</p>
        <p class="text-sm text-muted">
          &copy; {{ brand.copyrightYear }} {{ brand.name }}. {{ brand.footerNote }}
        </p>
      </div>
    </div>
  </footer>
</template>
