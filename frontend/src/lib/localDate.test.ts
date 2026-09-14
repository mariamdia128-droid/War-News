import { describe, expect, it } from "vitest";
import { getBeirutDate, normalizeDateInputValue } from "./localDate";

describe("getBeirutDate", () => {
  it("uses Beirut's calendar date when UTC is still on the previous day", () => {
    expect(getBeirutDate(0, new Date("2026-08-17T21:30:00.000Z"))).toBe("2026-08-18");
  });

  it("returns the previous Beirut calendar day", () => {
    expect(getBeirutDate(-1, new Date("2026-08-17T21:30:00.000Z"))).toBe("2026-08-17");
  });
});

describe("normalizeDateInputValue", () => {
  it("keeps valid date input values unchanged", () => {
    expect(normalizeDateInputValue("2026-08-01")).toBe("2026-08-01");
  });

  it("converts slash-delimited dates to date input values", () => {
    expect(normalizeDateInputValue("08/01/2026")).toBe("2026-08-01");
  });

  it("clears incomplete date placeholders", () => {
    expect(normalizeDateInputValue("08/01/yyyy")).toBe("");
  });
});
