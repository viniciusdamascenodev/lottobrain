import { resolveApiOrigin } from "./config/api-origin.mjs";

const environment = process.env.LOTTOBRAIN_ENV ?? (process.env.VERCEL ? "preview" : "local");
const apiOrigin = resolveApiOrigin(process.env.LOTTOBRAIN_API_ORIGIN, environment);

/** @type {import('next').NextConfig} */
const config = {
  poweredByHeader: false,
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${apiOrigin}/api/v1/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: [
      { key: "Cache-Control", value: "no-store" },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "no-referrer" },
    ] }];
  },
};
export default config;
