const path          = require("path");
const CopyPlugin    = require("copy-webpack-plugin");

module.exports = (env, argv) => {
  const isDev = argv.mode === "development";

  return {
    entry: {
      popup:      "./src/popup.ts",
      background: "./src/background.ts",
      content:    "./src/content.ts",
    },

    output: {
      path:     path.resolve(__dirname, "dist"),
      filename: "[name].js",
      clean:    true,
    },

    module: {
      rules: [
        {
          test: /\.ts$/,
          use:  "ts-loader",
          exclude: /node_modules/,
        },
      ],
    },

    resolve: {
      extensions: [".ts", ".js"],
    },

    devtool: isDev ? "inline-source-map" : false,

    plugins: [
      new CopyPlugin({
        patterns: [
          { from: "src/manifest.json", to: "manifest.json" },
          { from: "src/popup.html",    to: "popup.html"    },
          { from: "src/popup.css",     to: "popup.css"     },
          {
            from: "src/icons",
            to:   "icons",
            noErrorOnMissing: true,
          },
        ],
      }),
    ],

    optimization: {
      minimize: !isDev,
    },
  };
};