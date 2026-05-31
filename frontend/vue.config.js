const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  productionSourceMap: false,
  publicPath: './',
  outputDir: 'dist',
  assetsDir: 'assets',
  devServer: {
      port: 1024,
      host: '0.0.0.0',
      open: false,
      allowedHosts: 'all',
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          ws: true,
          changeOrigin: true,
        },
        '/images': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },

}})
