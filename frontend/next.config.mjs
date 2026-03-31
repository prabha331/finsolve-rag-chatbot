/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for the multi-stage Docker build.
  // Produces a self-contained .next/standalone directory that includes
  // a minimal node server — no full node_modules needed in the runner image.
  output: "standalone",
};

export default nextConfig;
