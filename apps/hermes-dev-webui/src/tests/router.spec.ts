import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '@/App.vue'
import { routes } from '@/router'
import { useThemeStore } from '@/stores/theme'

async function mountAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(App, {
    global: {
      plugins: [router],
    },
  })
  return { router, wrapper }
}

describe('Router', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('loads Workspace at root', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.find('.workspace-page').exists()).toBe(true)
  })

  it('loads Theme Lab at its route', async () => {
    const { wrapper } = await mountAt('/theme-lab')
    expect(wrapper.find('.theme-lab').exists()).toBe(true)
  })

  it('loads Dev Console at /console (Phase 2E)', async () => {
    const { wrapper } = await mountAt('/console')
    expect(wrapper.find('.devconsole').exists()).toBe(true)
    // The nav rail + overview section render.
    expect(wrapper.find('.devconsole-nav').exists()).toBe(true)
    expect(wrapper.find('[aria-label="Overview"]').exists()).toBe(true)
  })

  it('links from Workspace to Dev Console', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.get('.dev-console-link').attributes('href')).toBe('/console')
  })

  it('links from Dev Console back to Workspace', async () => {
    const { wrapper } = await mountAt('/console')
    expect(wrapper.get('.devconsole__back').attributes('href')).toBe('/')
  })

  it('links from Workspace to Theme Lab', async () => {
    const { wrapper } = await mountAt('/')
    expect(wrapper.get('.theme-lab-link').attributes('href')).toContain('/theme-lab')
  })

  it('links from Theme Lab back to Workspace', async () => {
    const { wrapper } = await mountAt('/theme-lab')
    expect(wrapper.get('.theme-lab__back').attributes('href')).toBe('/')
  })

  it('preserves theme state across route changes', async () => {
    const { router } = await mountAt('/')
    const store = useThemeStore()
    store.setTheme('song')
    await router.push('/theme-lab')
    expect(store.activeThemeId).toBe('song')
  })

  it('redirects unknown routes to Workspace', async () => {
    const { router, wrapper } = await mountAt('/not-a-route')
    expect(router.currentRoute.value.path).toBe('/')
    expect(wrapper.find('.workspace-page').exists()).toBe(true)
  })
})
