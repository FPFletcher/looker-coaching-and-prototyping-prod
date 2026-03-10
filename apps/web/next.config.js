/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        // Apply COEP and COOP to all routes including root
        source: '/(.*)', // Matches everything including the homepage
        headers: [
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'credentialless',
          },
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin-allow-popups',
          },
        ],
      },
    ];
  }
};
module.exports = nextConfig;