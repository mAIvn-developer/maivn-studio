import adapter from "@sveltejs/adapter-static";
import { vitePreprocess } from "@sveltejs/vite-plugin-svelte";

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),

  kit: {
    adapter: adapter({
      // Output to the static directory that FastAPI will serve
      pages: "../src/maivn_studio/static",
      assets: "../src/maivn_studio/static",
      fallback: "index.html",
      precompress: false,
      strict: true,
    }),
    paths: {
      base: "",
    },
  },
};

export default config;
