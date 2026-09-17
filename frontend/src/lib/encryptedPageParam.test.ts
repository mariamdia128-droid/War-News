import { describe, expect, it } from "vitest";
import { decodePageParam, encodePageParam } from "./encryptedPageParam";

describe("encrypted page params", () => {
  it("round-trips page numbers without exposing the raw number", () => {
    const token = encodePageParam(3);

    expect(token).not.toBe("3");
    expect(decodePageParam(token)).toBe(3);
  });

  it("keeps legacy plain page links working", () => {
    expect(decodePageParam("3")).toBe(3);
  });

  it("falls back to the first page for invalid values", () => {
    expect(decodePageParam("not-a-page")).toBe(1);
    expect(decodePageParam(null)).toBe(1);
  });
});
