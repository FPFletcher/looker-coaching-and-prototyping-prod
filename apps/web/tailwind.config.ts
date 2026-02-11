import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                background: "var(--background)",
                foreground: "var(--foreground)",
                gemini: {
                    blue: "#4285F4",
                    purple: "#A142F4",
                    sparkle: "#F4B400",
                },
                primary: "#1A73E8", // Google Blue
            },
            backgroundImage: {
                'gemini-gradient': 'linear-gradient(135deg, #4285F4 0%, #9013FE 100%)',
                'subtle-glow': 'radial-gradient(circle at 50% 50%, rgba(66, 133, 244, 0.1) 0%, transparent 50%)',
            }
        },
    },
    plugins: [],
};
export default config;
