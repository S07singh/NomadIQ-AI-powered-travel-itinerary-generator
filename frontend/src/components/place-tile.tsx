import Link from "next/link";
import type { MediaImage } from "@/lib/types";
import { Photo } from "./photo";

/**
 * A destination tile with its name and note set directly on the photo, editorial-style.
 * `image` is resolved server-side by the caller (see page.tsx) so this never shows a
 * client-side loading flash — it's a plain server component.
 */
export function PlaceTile({
  name,
  image,
  note,
  className,
  priority = false,
}: {
  name: string;
  image: MediaImage | null;
  note: string;
  className?: string;
  priority?: boolean;
}) {
  return (
    <Link href={`/explore/${encodeURIComponent(name)}`} className={`group relative block overflow-hidden rounded-sm bg-ink-soft ${className ?? ""}`}>
      {image ? (
        <Photo image={image} alt={name} priority={priority} className="h-full w-full transition-transform duration-700 ease-out group-hover:scale-105" />
      ) : (
        // Wikipedia had nothing for this query: a navy gradient reads as a deliberate tile, not a broken image.
        <div className="absolute inset-0 bg-gradient-to-br from-ink-soft to-board" aria-hidden />
      )}
      <div className="absolute inset-0 bg-gradient-to-t from-board/85 via-board/10 to-transparent" aria-hidden />
      <div className="absolute inset-x-0 bottom-0 p-4 sm:p-5">
        <h3 className="editorial text-2xl sm:text-[1.7rem] text-white">{name}</h3>
        <p className="mt-1 text-sm text-white/80 max-w-[34ch]">{note}</p>
      </div>
    </Link>
  );
}
