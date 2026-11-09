"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

// Sarvam's speech-to-text REST endpoint accepts clips up to 30s; auto-stop just under that
// so a long ramble still gets sent instead of being rejected.
const MAX_RECORDING_MS = 28_000;

/** Microphone recording via MediaRecorder. `stop()` resolves with the recorded audio. */
export function useRecorder(onAutoStop?: (audio: Blob | null) => void) {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const resolvers = useRef<((b: Blob | null) => void)[]>([]);
  const maxTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onAutoStopRef = useRef(onAutoStop);
  useEffect(() => {
    onAutoStopRef.current = onAutoStop;
  }, [onAutoStop]);

  const supported = typeof window !== "undefined" && "MediaRecorder" in window && !!navigator.mediaDevices?.getUserMedia;

  const start = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      chunks.current = [];
      rec.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      rec.onstop = () => {
        rec.stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        recorder.current = null;
        if (maxTimer.current) clearTimeout(maxTimer.current);
        const blob = chunks.current.length ? new Blob(chunks.current, { type: rec.mimeType || "audio/webm" }) : null;
        const pending = resolvers.current.splice(0);
        if (pending.length) pending.forEach((r) => r(blob));
        else onAutoStopRef.current?.(blob);
      };
      rec.start();
      recorder.current = rec;
      setRecording(true);
      maxTimer.current = setTimeout(() => recorder.current?.stop(), MAX_RECORDING_MS);
    } catch {
      setError("Microphone access was blocked. Allow it in your browser settings, or type instead.");
    }
  }, []);

  const stop = useCallback(
    () =>
      new Promise<Blob | null>((resolve) => {
        if (!recorder.current) return resolve(null);
        resolvers.current.push(resolve);
        recorder.current.stop();
      }),
    [],
  );

  return { supported, recording, error, start, stop };
}

/** Reads text aloud: Sarvam via the backend when configured, otherwise the browser's own voice. */
export async function speak(text: string, language?: string | null) {
  if (typeof window === "undefined" || !text.trim()) return;
  const blob = await api.speak(text, language);
  if (blob && blob.size > 0) {
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = audio.onerror = () => URL.revokeObjectURL(url);
    try {
      await audio.play();
      return;
    } catch {
      URL.revokeObjectURL(url);
      /* autoplay blocked or decode failed: fall through to on-device speech */
    }
  }
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.03;
    window.speechSynthesis.speak(u);
  }
}
