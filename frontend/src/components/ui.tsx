import clsx from "clsx";
import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

type Variant = "primary" | "ink" | "quiet" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-platform text-white hover:bg-platform-deep",
  ink: "bg-ink text-white hover:bg-ink-soft",
  quiet: "bg-transparent text-ink border-2 border-ink/80 hover:bg-ink hover:text-white",
  danger: "bg-transparent text-brick border-2 border-brick/70 hover:bg-brick hover:text-white",
};

const base =
  "inline-flex items-center justify-center gap-2 rounded-md px-4 h-11 font-bold text-[0.95rem] transition-colors disabled:opacity-50 disabled:pointer-events-none whitespace-nowrap";

export function Button({ variant = "primary", className, ...props }: ComponentProps<"button"> & { variant?: Variant }) {
  return <button className={clsx(base, variants[variant], className)} {...props} />;
}

export function ButtonLink({ variant = "primary", className, ...props }: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={clsx(base, variants[variant], className)} {...props} />;
}

export function Field({ label, hint, error, className, ...props }: ComponentProps<"input"> & { label: string; hint?: string; error?: string }) {
  return (
    <label className={clsx("block", className)}>
      <span className="block text-sm font-bold mb-1.5">{label}</span>
      <input
        className={clsx(
          "w-full h-11 rounded-md border-2 bg-sheet px-3 text-ink placeholder:text-slate/60 focus:outline-none focus:border-platform",
          error ? "border-brick" : "border-rule",
        )}
        {...props}
      />
      {error ? <span className="block text-sm text-brick mt-1">{error}</span> : hint ? <span className="block text-sm text-slate mt-1">{hint}</span> : null}
    </label>
  );
}

export function SelectField({ label, children, className, ...props }: ComponentProps<"select"> & { label: string }) {
  return (
    <label className={clsx("block", className)}>
      <span className="block text-sm font-bold mb-1.5">{label}</span>
      <select className="w-full h-11 rounded-md border-2 border-rule bg-sheet px-2.5 text-ink focus:outline-none focus:border-platform" {...props}>
        {children}
      </select>
    </label>
  );
}

export function Notice({ tone = "error", children }: { tone?: "error" | "info" | "success"; children: ReactNode }) {
  const styles = {
    error: "border-brick text-brick bg-brick/5",
    info: "border-ink/30 text-ink bg-sheet",
    success: "border-platform text-platform-deep bg-platform/5",
  }[tone];
  return (
    <p role={tone === "error" ? "alert" : "status"} className={clsx("border-l-4 px-4 py-3 rounded-r-md text-[0.95rem]", styles)}>
      {children}
    </p>
  );
}

export function Page({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={clsx("mx-auto w-full max-w-[1180px] px-4 sm:px-6 lg:px-8", className)}>{children}</div>;
}

export function PageTitle({ children, sub }: { children: ReactNode; sub?: ReactNode }) {
  return (
    <header className="pt-10 pb-8 sm:pt-14">
      <h1 className="display text-4xl sm:text-5xl">{children}</h1>
      {sub ? <p className="mt-3 text-slate text-lg max-w-[60ch]">{sub}</p> : null}
    </header>
  );
}

/** A station dot on the route. `filled` marks a reached/active station. */
export function Station({ filled = true, size = 16, className }: { filled?: boolean; size?: number; className?: string }) {
  return (
    <span
      aria-hidden
      className={clsx("inline-block shrink-0 rounded-full border-[3px] border-ink", filled ? "bg-signal" : "bg-sheet", className)}
      style={{ width: size, height: size }}
    />
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-16 text-slate" role="status">
      <Station filled={false} className="animate-pulse" />
      <span>{label}</span>
    </div>
  );
}
