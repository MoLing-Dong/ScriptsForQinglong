import path from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { getAllFiles } from "./Utils/MultipleEntrances.js";
export default {
  target: "node",
  // 入口文件为JavaScript下的所有文件
  //   entry: glob.sync("./JavaScript/*.js"),
  entry: getAllFiles("./JavaScript"),
  mode: "production", //development, production
  experiments: {
    outputModule: true,
  },
  output: {
    path: path.resolve(dirname(fileURLToPath(import.meta.url)), "dist"),
    filename: "[name].b.js",
    chunkFormat: "module",
  },
  resolve: {
    preferRelative: true,
  },
};
