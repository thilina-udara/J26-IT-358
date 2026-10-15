import { PHASE_DEVELOPMENT_SERVER } from "next/constants.js";

// Keep production builds from replacing a running development server's chunks.
export default function nextConfig(phase) {
  return {
    distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
  };
}
