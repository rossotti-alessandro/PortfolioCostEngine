import { describe, expect, it } from "vitest";
import { fitWithin, isPhoto, jpegName } from "./photos";

describe("photos", () => {
  it("shrinks the long side to the limit and never enlarges", () => {
    expect(fitWithin(4032, 3024)).toEqual({ w: 2400, h: 1800 });
    expect(fitWithin(3024, 4032)).toEqual({ w: 1800, h: 2400 });
    expect(fitWithin(800, 600)).toEqual({ w: 800, h: 600 });
  });
  it("names the re-encoded file as a JPEG", () => {
    expect(jpegName("IMG_1234.HEIC")).toBe("IMG_1234.jpg");
    expect(jpegName("scan.page.png")).toBe("scan.page.jpg");
  });
  it("recognises photos by type or extension, not PDFs", () => {
    expect(isPhoto(new File([""], "a.heic"))).toBe(true);
    expect(isPhoto(new File([""], "a", { type: "image/jpeg" }))).toBe(true);
    expect(isPhoto(new File([""], "a.pdf", { type: "application/pdf" }))).toBe(false);
  });
});
