"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Field, Notice, Page } from "./ui";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const { login, register } = useAuth();
  const router = useRouter();
  const next = useSearchParams().get("next") || "/trips";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isSignup = mode === "signup";

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isSignup) await register(name, email, password);
      else await login(email, password);
      router.replace(next);
    } catch (err) {
      setError(err instanceof ApiError ? friendly(err) : "Something went wrong. Try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page className="py-16 sm:py-24">
      <div className="max-w-[420px]">
        <h1 className="display text-4xl sm:text-5xl">{isSignup ? "Create your account" : "Welcome back"}</h1>
        <p className="mt-3 text-slate text-lg">{isSignup ? "Save trips, keep traveler details, and book in one step." : "Your trips and bookings are where you left them."}</p>
        <form onSubmit={submit} className="mt-10 space-y-5">
          {isSignup ? <Field label="Name" autoComplete="name" required value={name} onChange={(e) => setName(e.target.value)} /> : null}
          <Field label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field
            label="Password"
            type="password"
            autoComplete={isSignup ? "new-password" : "current-password"}
            required
            minLength={isSignup ? 8 : 1}
            hint={isSignup ? "At least 8 characters, with letters and numbers." : undefined}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error ? <Notice>{error}</Notice> : null}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? (isSignup ? "Creating account" : "Signing in") : isSignup ? "Create account" : "Sign in"}
          </Button>
        </form>
        <p className="mt-6 text-slate">
          {isSignup ? "Already have an account? " : "New to NomadIQ? "}
          <Link href={`${isSignup ? "/login" : "/signup"}?next=${encodeURIComponent(next)}`} className="font-bold text-platform hover:underline underline-offset-4">
            {isSignup ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </Page>
  );
}

function friendly(err: ApiError): string {
  if (err.code === "invalid_credentials") return "That email and password don't match. Check both and try again.";
  if (err.code === "email_taken") return "There's already an account with this email. Sign in instead.";
  if (err.code === "validation_error") return "Check the fields: passwords need 8+ characters with letters and numbers.";
  if (err.code === "rate_limited") return "Too many attempts. Wait a minute and try again.";
  return err.message;
}
