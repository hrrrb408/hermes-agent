import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import ThemeLabView from '@/views/ThemeLabView.vue'
import DevConsoleView from '@/views/DevConsoleView.vue'
import WorkspaceView from '@/views/WorkspaceView.vue'

export const routes: readonly RouteRecordRaw[] = [
    {
      path: '/',
      name: 'workspace',
      component: WorkspaceView,
    },
    {
      path: '/console',
      name: 'dev-console',
      component: DevConsoleView,
    },
    {
      path: '/theme-lab',
      name: 'theme-lab',
      component: ThemeLabView,
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
