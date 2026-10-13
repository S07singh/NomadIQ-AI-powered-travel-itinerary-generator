"use client";

/* eslint-disable @next/next/no-img-element -- photos come from many hosts (Wikimedia, Unsplash, suppliers) */
import clsx from "clsx";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MediaImage } from "@/lib/types";

export function Photo({ image, alt, className, credit = false, thumb = false }: { image?: MediaImage | null; alt?: string; className?: string; credit?: boolean; thumb?: boolean }) {
  const [failed, setFailed] = useState(false);
  if (!image || failed) {
    return <div className={clsx("bg-[repeating-linear-gradient(135deg,#e3e7ec_0_8px,#edf0f3_8px_16px)]", className)} aria-hidden />;
  }
  return (
    <figure className={clsx("relative overflow-hidden", className)}>
      <img src={(thumb && image.thumbnail_url) || image.url} alt={alt ?? image.alt} loading="lazy" decoding="async" onError={() => setFailed(true)} className="absolute inset-0 h-full w-full object-cover" />
      {credit && image.attribution ? (
        <figcaption className="absolute bottom-0 right-0 bg-ink/70 text-white text-[11px] px-1.5 py-0.5">{image.attribution}</figcaption>
      ) : null}
    </figure>
  );
}

/** Looks up a photo for a place name via the public explore API. */
export function PlacePhoto({ query, className }: { query: string; className?: string }) {
  const [image, setImage] = useState<MediaImage | null | undefined>(undefined);
  useEffect(() => {
    let alive = true;
    api
      .images(query, 1)
      .then((imgs) => alive && setImage(imgs[0] ?? null))
      .catch(() => alive && setImage(null));
    return () => {
      alive = false;
    };
  }, [query]);
  return <Photo image={image} alt={query} className={className} />;
}
