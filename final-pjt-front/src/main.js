import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import router from './router'
import VCalendar from 'v-calendar'
import 'v-calendar/style.css'

const app = createApp(App)
const pinia = createPinia()

// Pinia 플러그인 설정
pinia.use(piniaPluginPersistedstate)

// 앱에 플러그인 추가
app.use(pinia)
app.use(router)
app.use(VCalendar, {})

app.mount('#app')