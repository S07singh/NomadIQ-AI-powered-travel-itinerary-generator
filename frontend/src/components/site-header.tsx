"use client";

import clsx from "clsx";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/lib/auth";

const NAV = [
  { href: "/explore", label: "Explore" },
  { href: "/search", label: "Tickets & stays" },
  { href: "/trips", label: "My trips" },
  { href: "/bookings", label: "Bookings" },
  { href: "/assistant", label: "Assistant" },
];

export function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-2 font-extrabold text-xl tracking-tight" aria-label="NomadIQ home">
      <svg width="30" height="16" viewBox="0 0 30 16" aria-hidden>
        <line x1="4" y1="8" x2="26" y2="8" stroke="#FFC83D" strokeWidth="5" strokeLinecap="round" />
        <circle cx="5" cy="8" r="4" fill="#fff" stroke="#14213D" strokeWidth="2.5" />
        <circle cx="25" cy="8" r="4" fill="#FFC83D" stroke="#14213D" strokeWidth="2.5" />
      </svg>
      NomadIQ
    </Link>
  );
}

export function SiteHeader() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [open, setOpen] = useState(false);

  const links = NAV.map((item) => {
    const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
    return (
      <Link
        key={item.href}
        href={item.href}
        onClick={() => setOpen(false)}
        aria-current={active ? "page" : undefined}
        className={clsx(
          "font-semibold py-1 border-b-[3px] transition-colors",
          active ? "border-signal text-ink" : "border-transparent text-slate hover:text-ink",
        )}
      >
        {item.label}
      </Link>
    );
  });

  return (
    <header className="bg-sheet border-b border-rule sticky top-0 z-30">
      <div className="mx-auto max-w-[1180px] px-4 sm:px-6 lg:px-8 h-16 flex items-center gap-8">
        <Wordmark />
        <nav className="hidden md:flex items-center gap-6" aria-label="Main">
          {links}
        </nav>
        <div className="ml-auto hidden md:flex items-center gap-4">
          {loading ? null : user ? (
            <Link href="/profile" className="font-semibold text-slate hover:text-ink">
              {user.name.split(" ")[0]}
            </Link>
          ) : (
            <>
              <Link href="/login" className="font-semibold text-slate hover:text-ink">
                Sign in
              </Link>
              <Link href="/signup" className="h-10 px-4 inline-flex items-center rounded-md bg-ink text-white font-bold hover:bg-ink-soft">
                Create account
              </Link>
            </>
          )}
        </div>
        <button className="ml-auto md:hidden p-2 -mr-2" aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>
      {open ? (
        <nav className="md:hidden border-t border-rule px-4 py-4 flex flex-col gap-3 bg-sheet" aria-label="Main">
          {links}
          <Link href={user ? "/profile" : "/login"} onClick={() => setOpen(false)} className="font-semibold">
            {user ? "Profile" : "Sign in"}
          </Link>
        </nav>
      ) : null}
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-24 border-t border-rule">
      <div className="mx-auto max-w-[1180px] px-4 sm:px-6 lg:px-8 py-10 flex flex-col sm:flex-row gap-4 sm:items-center justify-between text-sm text-slate">
        <Wordmark />
        <p>Photos from Wikimedia Commons contributors. Weather by Open-Meteo.</p>
      </div>
    </footer>
  );
}
