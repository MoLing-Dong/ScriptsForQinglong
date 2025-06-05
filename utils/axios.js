/**
   * @Created by Mol on 2024/02/27
   * @description axios 实例
   */
const axios = require("axios");

// 创建一个自定义的 axios 实例
const customAxios = axios.create({
  // 基础 URL - 所有请求都会使用这个 URL 作为基础
  // 例如: 'https://api.example.com'
  //   baseURL: "https://your.api-base.url",
  // 设置请求超时时间（毫秒）
  timeout: 10000,
  // 设置默认请求头
  headers: {
    "User-Agent":
      "Mozilla/5.0 (Linux; Android 10; M2007J20CG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.181 Mobile Safari/537.36",
  },
});

// 添加请求拦截器
customAxios.interceptors.request.use(
  function (config) {
    // 在发送请求之前做些什么
    // 例如：可以在这里添加认证 token
    // config.headers.Authorization = `Bearer yourToken`;
    return config;
  },
  function (error) {
    // 对请求错误做些什么
    return Promise.reject(error);
  }
);

// 添加响应拦截器
customAxios.interceptors.response.use(
  function (response) {
    // 对响应数据做点什么
    return response.data;
  },
  function (error) {
    // 对响应错误做点什么
    return Promise.reject(error);
  }
);

// 导出自定义的 axios 实例
module.exports = customAxios;
