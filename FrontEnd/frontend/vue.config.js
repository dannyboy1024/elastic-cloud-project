const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer:{
    proxy:{
      '/route':{
        target: 'http://52.91.118.43:5000/',
        changeOrigin: true,
        pathRewrite: {
          '^/route': ''
        }
      }
    }
  }
})
