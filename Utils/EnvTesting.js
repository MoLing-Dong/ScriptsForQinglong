/* 
    用于检测当前环境,
    
 */
// 1. 是否是本地node环境
const isNode =
  typeof process !== "undefined" &&
  process.versions != null &&
  process.versions.node != null &&
  module &&
  !!module.exports;
// 2. 是否是浏览器环境
const isBrowser =
  typeof window !== "undefined" && typeof window.document !== "undefined";

//   检测是两者中的哪一个
const isNodeOrBrowser = isNode ? "node" : isBrowser ? "browser" : "unknow";

module.exports = isNodeOrBrowser;
