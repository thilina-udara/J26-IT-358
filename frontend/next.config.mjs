import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

// Keep production builds from replacing a running development server's chunks.
export default function nextConfig(phase) {
  return {
    // PP1 is restricted to the backend belonging to this working copy.
    env: { NEXT_PUBLIC_CULTIVATION_API_URL: "http://127.0.0.1:8001" },
    distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
  };
}
