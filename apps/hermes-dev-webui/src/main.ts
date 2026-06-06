import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router/index'
import { useThemeStore } from './stores/theme'

import './themes/styles/base.css'
import './themes/styles/obsidian.css'
import './themes/styles/paper.css'
import './themes/styles/song.css'
import './themes/styles/ink.css'
import './themes/styles/sakura-night.css'
import './styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

const themeStore = useThemeStore()
themeStore.initializeTheme()

app.mount('#app')
