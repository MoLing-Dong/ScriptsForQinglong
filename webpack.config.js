import { getAllFiles } from "./Utils/MultipleEntrances.js";
import TerserPlugin from "terser-webpack-plugin";
import webpack from "webpack";

export default {
  target: "node",
  // 入口文件为JavaScript下的所有文件
  entry: getAllFiles("./JavaScript"),
  mode: "production", //development, production
  experiments: {
    outputModule: true,
  },
  output: {
    // path: path.resolve(dirname(fileURLToPath(import.meta.url)), "dist"),
    filename: "[name].b.js",
    chunkFormat: "module",
  },
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({
        terserOptions: {
          output: {
            // comments: false,
          },
        },
        extractComments: false,
      }),
    ],
  },
  resolve: {
    preferRelative: true,
  },
  plugins: [
    new webpack.BannerPlugin({
      banner: "Your custom banner text goes here",
      entryOnly: true, // 仅在入口文件添加注释
    }),
  ],
};
