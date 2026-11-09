"use client";

import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "./ui";

/** The landing-page planner: a sentence with blanks. Hands off to /trips/new with the answers. */
export function PlannerSentence({ tone = "ink" }: { tone?: "ink" | "light" }) {
  const router = useRouter();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [days, setDays] = useState("4");
  const [start, setStart] = useState("");
  const [budget, setBudget] = useState("");
  const [currency, setCurrency] = useState("INR");
  const light = tone === "light";

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams({ to: to.trim(), days });
    if (from.trim()) params.set("from", from.trim());
    if (start) params.set("start", start);
    if (budget) params.set("budget", budget);
    params.set("currency", currency);
    router.push(`/trips/new?${params}`);
  };

  const width = (value: string, placeholder: string) => ({ width: `${Math.max(value.length, placeholder.length) + 1}ch` });
  const blank = clsx("blank", light && "blank-light");

  return (
    <form onSubmit={submit} className="max-w-[640px]">
      <p className={clsx("text-[1.55rem] sm:text-[1.9rem] leading-[1.75] font-semibold", light ? "text-white" : "text-ink")}>
        I&apos;m going from{" "}
        <input aria-label="Starting city" className={blank} placeholder="Bengaluru" value={from} onChange={(e) => setFrom(e.target.value)} style={width(from, "Bengaluru")} />{" "}
        to{" "}
        <input aria-label="Destination" required className={blank} placeholder="Jaipur" value={to} onChange={(e) => setTo(e.target.value)} style={width(to, "Jaipur")} /> for{" "}
        <input aria-label="Number of days" className={clsx(blank, "text-center")} type="number" min={1} max={30} value={days} onChange={(e) => setDays(e.target.value)} style={{ width: "2.6ch" }} />{" "}
        days, leaving{" "}
        <input aria-label="Start date" className={clsx(blank, "text-[0.8em]")} type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        , with about{" "}
        <select aria-label="Currency" className={clsx(blank, "text-[0.8em] pr-0")} value={currency} onChange={(e) => setCurrency(e.target.value)}>
          <option value="INR">₹</option>
          <option value="USD">$</option>
          <option value="EUR">€</option>
          <option value="GBP">£</option>
        </select>
        <input aria-label="Budget" className={blank} inputMode="numeric" placeholder="40,000" value={budget} onChange={(e) => setBudget(e.target.value.replace(/[^\d]/g, ""))} style={width(budget, "40,000")} /> to spend.
      </p>
      <div className="mt-8 flex flex-wrap items-center gap-4">
        <Button type="submit" variant={light ? "signal" : "primary"} className="h-13 px-6 text-base">
          Draw my route
        </Button>
        <span className={light ? "text-white/70" : "text-slate"}>Takes about a minute. You can change anything after.</span>
      </div>
    </form>
  );
}
