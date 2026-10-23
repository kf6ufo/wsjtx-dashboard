import { createApp } from 'vue'
import 'bootstrap/dist/css/bootstrap.min.css'
import './style.css'
import App from './App.vue'
import { createDashboard } from './focus'
import { connectLive } from './live'
const live = new URLSearchParams(window.location.search).get('mode') !== 'demo'
const dashboard = createDashboard(undefined, live)
if (live) connectLive(dashboard)
createApp(App, { dashboard }).mount('#app')
