/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",       // Render static site olarak yayınlanır (render.yaml → jsaas-panel)
  trailingSlash: true,
  images: { unoptimized: true },
};
export default nextConfig;
