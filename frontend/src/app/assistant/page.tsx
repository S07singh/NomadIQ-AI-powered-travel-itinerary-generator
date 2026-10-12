"use client";

import clsx from "clsx";
import { Mic, Square } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { OfferRow } from "@/components/offers";
import { Button, Loading, Notice, Page } from "@/components/ui";
import { ApiError, api } from "@/lib/api";
import { useRequireUser } from "@/lib/auth";
import { money } from "@/lib/format";
import { speak, useRecorder } from "@/lib/use-recorder";
import type { AssistantAction, AssistantMessage } from "@/lib/types";

const STARTERS = ["Plan 3 days in Udaipur in December", "Find a train from Delhi to Jaipur next Friday", "Hotels in Goa for the long weekend", "Food tours in Lisbon"];

function Actions({ actions, onBook, busy }: { actions: AssistantAction[]; onBook: (offerId: string) => void; busy: boolean }) {
  return (
    <>
      {actions.map((a, i) => {
        if (a.type === "show_offers")
          return (
            <ul key={i} className="mt-3 divide-y divide-rule border-y border-rule bg-sheet">
              {a.data.results.map((o) => (
                <li key={o.offer_id} className="p-4">
                  <OfferRow offer={o} action={<Button variant="quiet" disabled={busy} onClick={() => onBook(o.offer_id)}>Book this</Button>} />
                </li>
              ))}
            </ul>
          );
        if (a.type === "booking_quote")
          return (
            <div key={i} className="mt-3 border-l-4 border-signal bg-sheet px-4 py-3 flex flex-wrap items-center justify-between gap-3">
              <span>
                Price held at <strong className="tabular">{money(a.data.price)}</strong>. Nothing is charged until you confirm.
              </span>
              <Link href={`/bookings/${a.data.booking_id}`} className="font-bold text-platform hover:underline underline-offset-4">
                Review and pay
              </Link>
            </div>
          );
        if (a.type === "trip_created")
          return (
            <Link key={i} href={`/trips/${a.data.trip_id}`} className="mt-3 inline-block font-bold text-platform hover:underline underline-offset-4">
              Watch the {a.data.destination} route being drawn
            </Link>
          );
        if (a.type === "trip_updated")
          return (
            <Link key={i} href={`/trips/${a.data.trip_id}`} className="mt-3 inline-block font-bold text-platform hover:underline underline-offset-4">
              Open the updated trip
            </Link>
          );
        if (a.type === "needs_info" && a.data.missing.includes("saved_traveler"))
          return (
            <Link key={i} href="/profile" className="mt-3 inline-block font-bold text-platform hover:underline underline-offset-4">
              Add traveler details
            </Link>
          );
        return null;
      })}
    </>
  );
}

export default function AssistantPage() {
  const user = useRequireUser();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRecorder();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Block body on purpose: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup.
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (!user) return <Page><Loading /></Page>;

  const push = (m: AssistantMessage) => setMessages((cur) => [...cur, m]);
  const local = (content: string): AssistantMessage => ({ id: `local-${Date.now()}`, role: "user", content, actions: [], created_at: new Date().toISOString() });

  const send = async (message: string, selectedOfferId?: string) => {
    if (!message.trim()) return;
    setBusy(true);
    setError(null);
    push(local(message));
    setText("");
    try {
      const reply = await api.ask({ message, conversation_id: conversationId, selected_offer_id: selectedOfferId });
      setConversationId(reply.conversation_id);
      push(reply.message);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The assistant didn't answer. Try again.");
    } finally {
      setBusy(false);
    }
  };

  const toggleMic = async () => {
    if (!recorder.recording) return recorder.start();
    const audio = await recorder.stop();
    if (!audio) return;
    setBusy(true);
    setError(null);
    try {
      const reply = await api.voice(audio, { conversation_id: conversationId });
      setConversationId(reply.conversation_id);
      push(local(reply.transcript ?? "(voice)"));
      push(reply.message);
      speak(reply.message.content);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't make out that recording. Try again or type.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page className="pb-10">
      <header className="pt-10 pb-6">
        <h1 className="display text-4xl sm:text-5xl">Assistant</h1>
        <p className="mt-3 text-lg text-slate max-w-[60ch]">Ask for a plan, a fare or a room. It can hold a price for you, but you always confirm before anything is paid.</p>
      </header>

      <div className="max-w-[860px]">
        {messages.length === 0 ? (
          <div className="flex flex-wrap gap-2 mb-8">
            {STARTERS.map((s) => (
              <button key={s} onClick={() => send(s)} className="text-left font-semibold border-2 border-rule bg-sheet rounded-md px-4 py-2.5 hover:border-ink">
                {s}
              </button>
            ))}
          </div>
        ) : null}

        <ol className="space-y-6" aria-live="polite">
          {messages.map((m) => (
            <li key={m.id} className={clsx(m.role === "user" ? "flex justify-end" : "")}>
              {m.role === "user" ? (
                <p className="bg-ink text-white rounded-md px-4 py-2.5 max-w-[80%]">{m.content}</p>
              ) : (
                <div className="border-l-4 border-ink pl-4">
                  <p className="text-[1.05rem] max-w-[65ch]">{m.content}</p>
                  <Actions actions={m.actions} busy={busy} onBook={(id) => send("Book this one", id)} />
                </div>
              )}
            </li>
          ))}
          {busy ? (
            <li className="border-l-4 border-rule pl-4 text-slate" role="status">
              Working on it
            </li>
          ) : null}
        </ol>
        <div ref={endRef} />

        {error || recorder.error ? <div className="mt-6"><Notice>{error ?? recorder.error}</Notice></div> : null}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(text);
          }}
          className="sticky bottom-4 mt-8 flex gap-2 bg-sheet border-2 border-ink rounded-md p-2 shadow-[0_6px_0_0_rgba(20,33,61,0.12)]"
        >
          {recorder.supported ? (
            <button
              type="button"
              onClick={toggleMic}
              disabled={busy}
              aria-pressed={recorder.recording}
              aria-label={recorder.recording ? "Stop recording and send" : "Speak instead of typing"}
              className={clsx("w-12 h-12 shrink-0 rounded-md inline-flex items-center justify-center", recorder.recording ? "bg-brick text-white" : "bg-signal text-ink hover:bg-signal-deep")}
            >
              {recorder.recording ? <Square size={18} /> : <Mic size={20} />}
            </button>
          ) : null}
          <label htmlFor="assistant-input" className="sr-only">Message</label>
          <input
            id="assistant-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={recorder.recording ? "Listening. Tap the square to send." : "Sleeper bus from Bengaluru to Goa on Friday"}
            maxLength={2000}
            className="flex-1 min-w-0 h-12 px-3 text-lg focus:outline-none"
          />
          <Button type="submit" disabled={busy || !text.trim()} className="h-12">Send</Button>
        </form>
      </div>
    </Page>
  );
}
