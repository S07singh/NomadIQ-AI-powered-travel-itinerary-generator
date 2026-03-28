"use client";

import { useState } from "react";
import Link from "next/link";
import { useSession, signOut } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Compass, Menu, X, LogOut, User } from "lucide-react";

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: session, status } = useSession();
  const isLoggedIn = status === "authenticated";

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/80 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-6xl mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center">
            <Compass className="w-4 h-4 text-white" />
          </div>
          <span className="text-xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
            NomadIQ
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden md:flex items-center gap-6">
          <Link
            href="/"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Home
          </Link>
          <Link
            href="/plan"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Plan a Trip
          </Link>
          {isLoggedIn && (
            <Link
              href="/plans"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              My Trips
            </Link>
          )}

          {isLoggedIn ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                {session?.user?.image ? (
                  <img
                    src={session.user.image}
                    alt=""
                    className="w-7 h-7 rounded-full"
                  />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-emerald-100 flex items-center justify-center">
                    <User className="w-3.5 h-3.5 text-emerald-700" />
                  </div>
                )}
                <span className="text-sm font-medium">
                  {session?.user?.name?.split(" ")[0] || "User"}
                </span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => signOut({ callbackUrl: "/" })}
                className="text-muted-foreground"
              >
                <LogOut className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Link href="/login">
                <Button variant="ghost" size="sm">
                  Login
                </Button>
              </Link>
              <Link href="/signup">
                <Button
                  size="sm"
                  className="bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
                >
                  Sign Up
                </Button>
              </Link>
            </div>
          )}
        </nav>

        {/* Mobile Menu Toggle */}
        <button
          className="md:hidden"
          onClick={() => setMobileOpen(!mobileOpen)}
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Nav */}
      {mobileOpen && (
        <div className="md:hidden border-t bg-white px-4 py-3 space-y-3">
          <Link
            href="/"
            className="block text-sm font-medium"
            onClick={() => setMobileOpen(false)}
          >
            Home
          </Link>
          <Link
            href="/plan"
            className="block text-sm font-medium"
            onClick={() => setMobileOpen(false)}
          >
            Plan a Trip
          </Link>
          {isLoggedIn && (
            <Link
              href="/plans"
              className="block text-sm font-medium"
              onClick={() => setMobileOpen(false)}
            >
              My Trips
            </Link>
          )}
          {isLoggedIn ? (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                signOut({ callbackUrl: "/" });
                setMobileOpen(false);
              }}
              className="w-full justify-start"
            >
              <LogOut className="w-4 h-4 mr-2" /> Sign out
            </Button>
          ) : (
            <div className="flex gap-2">
              <Link href="/login" className="flex-1">
                <Button variant="outline" size="sm" className="w-full">
                  Login
                </Button>
              </Link>
              <Link href="/signup" className="flex-1">
                <Button
                  size="sm"
                  className="w-full bg-gradient-to-r from-emerald-500 to-teal-600 text-white"
                >
                  Sign Up
                </Button>
              </Link>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
