import type { Metadata, Viewport } from "next";
import { Fraunces, Overpass } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import { SiteFooter, SiteHeader } from "@/components/site-header";

const overpass = Overpass({ subsets: ["latin"], weight: ["400", "600", "700", "800"], variable: "--font-overpass", display: "swap" });
// Reserved for destination names and hero headlines only — a warm, editorial counterweight
// to Overpass's mechanical signage feel. Never used in UI chrome, buttons, or data.
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["500", "600"],
  style: ["normal", "italic"],
  variable: "--font-fraunces",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "NomadIQ: plan the trip, book the seats", template: "%s | NomadIQ" },
  description: "Day-by-day trip plans with photos, weather and real prices. Book flights, trains, buses and hotels in the same place.",
};

export const viewport: Viewport = { themeColor: "#14213D" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${overpass.variable} ${fraunces.variable}`}>
      {/* suppressHydrationWarning: browser extensions (e.g. ColorZilla) inject attributes like
          cz-shortcut-listen onto <body> before React hydrates, which is a false-positive mismatch. */}
      <body className="antialiased min-h-dvh flex flex-col" suppressHydrationWarning>
        <AuthProvider>
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 bg-signal px-3 py-2 font-bold">
            Skip to content
          </a>
          <SiteHeader />
          <main id="main" className="flex-1">{children}</main>
          <SiteFooter />
        </AuthProvider>
      </body>
    </html>
  );
}
