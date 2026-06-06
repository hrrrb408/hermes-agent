import { createRouter, createWebHashHistory } from 'vue-router'
import ThemeLabView from '@/views/ThemeLabView.vue'

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      name: 'theme-lab',
      component: ThemeLabView,
    },
  ],
})
