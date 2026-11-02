<script setup>
import { computed, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import Header from '@/components/layout/Header.vue'
import MobileDrawer from '@/components/layout/MobileDrawer.vue'
import Footer from '@/components/layout/Footer.vue'
import ListeningModal from '@/components/ui/modals/ListeningModal.vue'

const drawerOpen = ref(false)

// Routes with meta.layout === 'auth' render their own full-screen layout (no header or footer).
const route = useRoute()
const showChrome = computed(() => route.meta.layout !== 'auth')
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-navy-950">
    <template v-if="showChrome">
      <Header @open-menu="drawerOpen = true" />
      <MobileDrawer v-model="drawerOpen" />
    </template>

    <main>
      <RouterView />
    </main>

    <Footer v-if="showChrome" />

    <!-- Interactive feature #2: modal opened from the hero play button -->
    <ListeningModal />
  </div>
</template>
