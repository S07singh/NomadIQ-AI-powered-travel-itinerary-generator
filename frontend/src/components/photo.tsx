"use client";

/* eslint-disable @next/next/no-img-element -- photos come from many hosts (Wikimedia, Unsplash, suppliers) */
import clsx from "clsx";
import { useState } from "react";
import type { MediaImage } from "@/lib/types";

export function Photo({
  image,
  alt,
  className,
  credit = false,
  thumb = false,
  priority = false,
}: {
  image?: MediaImage | null;
  alt?: string;
  className?: string;
  credit?: boolean;
  thumb?: boolean;
  /** For photos that sit above or just below the fold (e.g. a destination showcase grid):
   *  loads immediately instead of waiting for native lazy-load to decide it's near the viewport. */
  priority?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  if (!image || failed) {
    return <div className={clsx("bg-[repeating-linear-gradient(135deg,#e3e7ec_0_8px,#edf0f3_8px_16px)]", className)} aria-hidden />;
  }
  return (
    <figure className={clsx("relative overflow-hidden", className)}>
      <img
        src={(thumb && image.thumbnail_url) || image.url}
        alt={alt ?? image.alt}
        loading={priority ? "eager" : "lazy"}
        fetchPriority={priority ? "high" : "auto"}
        decoding="async"
        onError={() => setFailed(true)}
        className="absolute inset-0 h-full w-full object-cover"
      />
      {credit && image.attribution ? (
        <figcaption className="absolute bottom-0 right-0 bg-ink/70 text-white text-[11px] px-1.5 py-0.5">{image.attribution}</figcaption>
      ) : null}
    </figure>
  );
}
