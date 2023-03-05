import Vue from 'vue'
import App from './App.vue'
import router from './views/Router.js'

Vue.config.productionTip = false

new Vue({
  render: h => h(App),
  router: router
}).$mount('#app')
