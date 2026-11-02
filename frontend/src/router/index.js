import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '@/pages/landing/page.vue'
import DetailPage from '@/pages/detail/page.vue'

// One landing page. The first four routes render it and scroll to their section (meta.section).
const routes = [
  { path: '/', name: 'home', component: LandingPage, meta: { title: 'Home', section: 'home' } },
  { path: '/about', name: 'about', component: LandingPage, meta: { title: 'About', section: 'about' } },
  {
    path: '/subscription',
    name: 'subscription',
    component: LandingPage,
    meta: { title: 'Subscription', section: 'subscription' },
  },
  { path: '/contact', name: 'contact', component: LandingPage, meta: { title: 'Contact', section: 'contact' } },
  // Dynamic route: /detail/free, /detail/pro, /detail/pro-max, /detail/lifetime
  { path: '/detail/:id', name: 'detail', component: DetailPage, meta: { title: 'Plan detail' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, saved) {
    if (saved) return saved
    if (to.meta.section) {
      if (to.meta.section === 'home') return { top: 0, behavior: 'smooth' }
      return { el: `#${to.meta.section}`, behavior: 'smooth' }
    }
    return { top: 0 }
  },
})

router.afterEach((to) => {
  document.title = `${to.meta.title ?? 'Page'} | False Speech`
})

export default router
