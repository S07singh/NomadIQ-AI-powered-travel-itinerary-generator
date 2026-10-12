"use client";

import clsx from "clsx";
import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "@/lib/api";
import type { Trip, TripMessage } from "@/lib/types";
import { Button } from "../ui";

const SUGGESTIONS = ["Make day 2 slower", "Swap a sight for a food walk", "Cut the cost by a fifth"];

export function TripChat({ trip, onUpdated }: { trip: Trip; onUpdated: (t: Trip) => void }) {
  const [messages, setMessages] = useState<TripMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLOListElement>(null);

  useEffect(() => {
    api.tripChatHistory(trip.id).then(setMessages).catch(() => undefined);
  }, [trip.id]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [messages]);

  const send = async (message: string) => {
    if (!message.trim()) return;
    setBusy(true);
    setError(null);
    const optimistic: TripMessage = { id: `local-${Date.now()}`, role: "user", content: message, created_at: new Date().toISOString() };
    setMessages((m) => [...m, optimistic]);
    setText("");
    try {
      const res = await api.tripChat(trip.id, message);
      setMessages((m) => [...m, res.reply]);
      if (res.plan_updated) onUpdated(res.trip);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That didn't go through. Try again.");
      setMessages((m) => m.filter((x) => x.id !== optimistic.id));
      setText(message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section aria-label="Change this trip" className="border-2 border-ink rounded-md bg-sheet flex flex-col max-h-[560px]">
      <header className="px-4 py-3 border-b-2 border-ink">
        <h2 className="heading text-lg">Change something</h2>
        <p className="text-sm text-slate">Ask in plain words. The route redraws when the plan changes.</p>
      </header>
      <ol ref={listRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-[120px]">
        {messages.length === 0 ? (
          <li className="flex flex-wrap gap-2">
            {SUGGESTIONS.map((s) => (
              <button key={s} onClick={() => send(s)} disabled={busy} className="text-sm font-semibold border-2 border-rule rounded-full px-3 py-1 hover:border-ink">
                {s}
              </button>
            ))}
          </li>
        ) : (
          messages.map((m) => (
            <li key={m.id} className={clsx("max-w-[90%] rounded-md px-3 py-2", m.role === "user" ? "ml-auto bg-ink text-white" : "bg-paper")}>
              {m.content}
              {m.role === "assistant" && m.plan_version ? <span className="block text-xs text-slate mt-1">Route version {m.plan_version}</span> : null}
            </li>
          ))
        )}
      </ol>
      {error ? <p className="px-4 text-sm text-brick">{error}</p> : null}
      <form
        className="flex gap-2 p-3 border-t border-rule"
        onSubmit={(e) => {
          e.preventDefault();
          send(text);
        }}
      >
        <label className="sr-only" htmlFor="trip-chat-input">Message</label>
        <input
          id="trip-chat-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Add a sunset spot on day 3"
          maxLength={1000}
          className="flex-1 min-w-0 h-11 rounded-md border-2 border-rule px-3 focus:outline-none focus:border-platform"
        />
        <Button type="submit" disabled={busy || !text.trim()}>{busy ? "Updating" : "Send"}</Button>
      </form>
    </section>
  );
}
