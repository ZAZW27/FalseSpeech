import { createRouter, createWebHistory } from 'vue-router'
import LandingLayout from '@/components/layout/LandingLayout.vue'
const LandingPage = () => import('@/pages/landing/page.vue')
const DetailPage = () => import('@/pages/detail/page.vue')
const LoginPage = () => import('@/pages/login/page.vue')
const RegisterPage = () => import('@/pages/register/page.vue')
const DashboardPage = () => import('@/pages/dashboard/page.vue')
const HistoryPage = () => import('@/pages/history/page.vue')
const ProfilePage = () => import('@/pages/profile/page.vue')

const routes = [
  {
    path: '/',
    component: LandingLayout,
    children: [
      { path: '', name: 'home', component: LandingPage, meta: { title: 'Home', section: 'home' } },
      { path: 'about', name: 'about', component: LandingPage, meta: { title: 'About', section: 'about' } },
      {
        path: 'subscription',
        name: 'subscription',
        component: LandingPage,
        meta: { title: 'Subscription', section: 'subscription' },
      },
      { path: 'contact', name: 'contact', component: LandingPage, meta: { title: 'Contact', section: 'contact' } },
      // Dynamic route: /detail/free, /detail/pro, /detail/pro-max, /detail/lifetime
      { path: 'detail/:id', name: 'detail', component: DetailPage, meta: { title: 'Plan detail' } },
    ],
  },

  // Standalone pages. These do not use LandingLayout.
  { path: '/login', name: 'login', component: LoginPage, meta: { title: 'Log in' } },
  { path: '/register', name: 'register', component: RegisterPage, meta: { title: 'Sign up' } },
  { path: '/dashboard', name: 'dashboard', component: DashboardPage, meta: { title: 'Dashboard' } },
  { path: '/history', name: 'history', component: HistoryPage, meta: { title: 'History' } },
  { path: '/profile', name: 'profile', component: ProfilePage, meta: { title: 'Profile' } },
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
