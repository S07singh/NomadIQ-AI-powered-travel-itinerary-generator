import type { Metadata, Viewport } from "next";
import { Overpass } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { SiteFooter, SiteHeader } from "@/components/site-header";

const overpass = Overpass({ subsets: ["latin"], weight: ["400", "600", "700", "800"], variable: "--font-overpass", display: "swap" });

export const metadata: Metadata = {
  title: { default: "NomadIQ: plan the trip, book the seats", template: "%s | NomadIQ" },
  description: "Day-by-day trip plans with photos, weather and real prices. Book flights, trains, buses and hotels in the same place.",
};

export const viewport: Viewport = { themeColor: "#14213D" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={overpass.variable}>
      <body className="antialiased">
        <AuthProvider>
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 bg-signal px-3 py-2 font-bold">
            Skip to content
          </a>
          <SiteHeader />
          <main id="main">{children}</main>
          <SiteFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
