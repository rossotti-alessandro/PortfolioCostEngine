/** Phone photos, shrunk in the browser before upload (SC-8.28).
 *
 * A phone shot is 3-12 MB; OCR needs about 300 dpi on an A4 page, which is ~2500 px on the long side.
 * Re-encoding as JPEG also turns an iPhone HEIC into a JPEG where the browser can decode it (Safari),
 * and drops EXIF location data before the file leaves the phone. */

export const PHOTO_EXT = [".jpg", ".jpeg", ".png", ".heic", ".heif"];
export const MAX_SIDE = 2400;
const QUALITY = 0.85;

export const isPhoto = (f: File) =>
  f.type.startsWith("image/") || PHOTO_EXT.some((e) => f.name.toLowerCase().endsWith(e));

/** Target size that keeps the aspect ratio and never enlarges. */
export function fitWithin(w: number, h: number, max = MAX_SIDE): { w: number; h: number } {
  const k = Math.min(1, max / Math.max(w, h));
  return { w: Math.round(w * k), h: Math.round(h * k) };
}

/** `IMG_1234.HEIC` → `IMG_1234.jpg`. */
export const jpegName = (name: string) => `${name.replace(/\.[^.]+$/, "") || "page"}.jpg`;

/** Decode (EXIF rotation applied by the browser), shrink, re-encode as JPEG. Throws when the browser cannot read it. */
export async function shrinkPhoto(f: File): Promise<File> {
  const bmp = await createImageBitmap(f, { imageOrientation: "from-image" });
  const { w, h } = fitWithin(bmp.width, bmp.height);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("no canvas");
  ctx.drawImage(bmp, 0, 0, w, h);
  bmp.close();
  const blob = await new Promise<Blob | null>((ok) => canvas.toBlob(ok, "image/jpeg", QUALITY));
  if (!blob) throw new Error("could not encode the photo");
  return new File([blob], jpegName(f.name), { type: "image/jpeg" });
}
