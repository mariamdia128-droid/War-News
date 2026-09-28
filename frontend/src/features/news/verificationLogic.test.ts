import { describe, expect, it } from "vitest";
import { verificationTypeFromSearch, verificationTypeLabel } from "./verificationLogic";

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
});
