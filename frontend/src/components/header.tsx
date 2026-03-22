"use client";

import Link from "next/link";
import { Plane, Menu, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-md">
      <div className="max-w-6xl mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-bold text-xl">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Plane className="w-4 h-4 text-white" />
          </div>
          <span className="bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
            NomadIQ
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-6">
          <Link href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Home
          </Link>
          <Link href="/plan" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Plan a Trip
          </Link>
          <Link href="/plans" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            My Trips
          </Link>
          <Link href="/plan">
            <Button size="sm" className="bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-md">
              <Plane className="w-3 h-3 mr-1.5" /> Plan Trip
            </Button>
          </Link>
        </nav>

        {/* Mobile toggle */}
        <button className="md:hidden" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-background px-4 py-4 space-y-3">
          <Link href="/" className="block text-sm" onClick={() => setMobileOpen(false)}>Home</Link>
          <Link href="/plan" className="block text-sm" onClick={() => setMobileOpen(false)}>Plan a Trip</Link>
          <Link href="/plans" className="block text-sm" onClick={() => setMobileOpen(false)}>My Trips</Link>
        </div>
      )}
    </header>
  );
}
