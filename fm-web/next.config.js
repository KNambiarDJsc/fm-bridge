/** @type {import('next').NextConfig} */
const nextConfig = {
    env: {
        BRIDGE_URL: process.env.BRIDGE_URL || "http://localhost:8002",
        AGENTS_URL: process.env.AGENTS_URL || "http://localhost:8003",
    },
};
module.exports = nextConfig;
