import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "https://goblurry-academic-ai-agent.hf.space",
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ""),
        configure(proxy) {
          proxy.on("proxyRes", (res) => {
            if (res.headers["set-cookie"])
              res.headers["set-cookie"] = res.headers["set-cookie"].map((c) =>
                c
                  .replace(/;\s*Secure/gi, "")
                  .replace(/SameSite=none/gi, "SameSite=Lax"),
              );
          });
        },
      },
    },
  },
});
