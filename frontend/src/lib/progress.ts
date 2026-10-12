// Live trip-generation progress. Uses the SSE endpoint through fetch (EventSource can't send
// an Authorization header) and falls back to polling /status if streaming isn't available.

import { API_URL, api, tokens } from "./api";
import type { TripProgress } from "./types";

const DONE = new Set(["ready", "failed", "draft"]);

export function watchTripProgress(tripId: string, onProgress: (p: TripProgress) => void): () => void {
  const controller = new AbortController();
  let stopped = false;

  const poll = async () => {
    while (!stopped) {
      try {
        const p = await api.tripStatus(tripId);
        onProgress(p);
        if (DONE.has(p.status)) return;
      } catch {
        /* transient: keep polling */
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
  };

  (async () => {
    try {
      const res = await fetch(`${API_URL}/trips/${tripId}/events`, {
        headers: { Authorization: `Bearer ${tokens.get()?.access_token ?? ""}` },
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error("no stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (!stopped) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";
        for (const evt of events) {
          const data = evt.split("\n").find((l) => l.startsWith("data:"));
          if (!data) continue;
          const parsed = JSON.parse(data.slice(5)) as TripProgress;
          if (parsed && "status" in parsed) onProgress(parsed);
        }
      }
    } catch {
      if (!stopped) await poll();
    }
  })();

  return () => {
    stopped = true;
    controller.abort();
  };
}
