<script setup>
import { ref } from 'vue'
import { RouterView } from 'vue-router'
import Header from '@/components/layout/Header.vue'
import MobileDrawer from '@/components/layout/MobileDrawer.vue'
import Footer from '@/components/layout/Footer.vue'
import ListeningModal from '@/components/ui/modals/ListeningModal.vue'

const drawerOpen = ref(false)
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-navy-950">
    <Header @open-menu="drawerOpen = true" />
    <MobileDrawer v-model="drawerOpen" />

    <main>
      <!-- Nested routes render their page through RouterView. A slot can override it. -->
      <slot>
        <RouterView />
      </slot>
    </main>

    <Footer />

    <!-- Interactive feature #2: modal opened from the hero play button -->
    <ListeningModal />
  </div>
</template>
