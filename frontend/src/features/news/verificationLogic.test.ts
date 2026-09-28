import { describe, expect, it } from "vitest";
import {
  ALL_DATES_RANGE,
  hasNonDefaultFilters,
  isVerificationView,
  outsideRangeNotice,
  verificationTypeFromSearch,
  verificationTypeLabel,
} from "./verificationLogic";

describe("incident verification filters", () => {
  it("reads supported check types from URL state", () => {
    expect(verificationTypeFromSearch("?verification_type=casualty_missing_number")).toBe("casualty_missing_number");
    expect(verificationTypeFromSearch("?verification_type=unknown")).toBeUndefined();
  });

  it("maps payload types to row chip labels", () => {
    expect(verificationTypeLabel("duplicate")).toBe("Duplicate");
    expect(verificationTypeLabel("casualty_missing_number")).toBe("Missing number");
    expect(verificationTypeLabel("casualty_aggregate_toll")).toBe("Aggregate toll");
  });

  it("shows the outside-range notice only for a positive count", () => {
    expect(outsideRangeNotice(undefined)).toBeNull();
    expect(outsideRangeNotice(0)).toBeNull();
    expect(outsideRangeNotice(1)).toBe("1 more flagged incident outside this date range");
    expect(outsideRangeNotice(4)).toBe("4 more flagged incidents outside this date range");
  });

  it("treats needs verification or any check type as a verification view", () => {
    expect(isVerificationView("needs_verification", "")).toBe(true);
    expect(isVerificationView("", "duplicate")).toBe(true);
    expect(isVerificationView("verified", "")).toBe(false);
    expect(isVerificationView("", "")).toBe(false);
  });

  it("does not count the default date range as an active filter", () => {
    const defaults = { from: "2026-08-20", to: "2026-09-28" };
    const empty = { village: "", verificationType: "", hasCasualties: false };
    expect(hasNonDefaultFilters(empty, defaults.from, defaults.to, defaults)).toBe(false);
    expect(hasNonDefaultFilters(empty, ALL_DATES_RANGE.from, ALL_DATES_RANGE.to, defaults)).toBe(true);
    expect(hasNonDefaultFilters({ ...empty, verificationType: "duplicate" }, defaults.from, defaults.to, defaults)).toBe(true);
    expect(hasNonDefaultFilters({ ...empty, hasCasualties: true }, defaults.from, defaults.to, defaults)).toBe(true);
  });
});
