const { defineConfig } = require('@vue/cli-service')
module.exports = defineConfig({
  transpileDependencies: true,
  devServer:{
    proxy:{
      '/route':{
        target: 'http://34.201.165.165:5000/',
        changeOrigin: true,
        pathRewrite: {
          '^/route': ''
        }
      }
    }
  }
})
