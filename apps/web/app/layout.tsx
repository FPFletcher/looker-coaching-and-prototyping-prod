import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./global.css";
import clsx from "clsx";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Banana - Looker Prototype Agent",
    description: "Generate Looker dashboards and data from a single prompt.",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={clsx(inter.className, "bg-gray-900 text-white min-h-screen")}>
                {children}
            </body>
        </html>
    );
}
