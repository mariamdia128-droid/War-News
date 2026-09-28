import { describe, expect, it } from "vitest";
import { assignedTotal, buildResolutionEntries, canSubmitResolution, dismissReasonError, filtersFromSearch, filtersToSearch, isOverTotal, mapApiError, mapFieldErrors } from "./logic";

describe("casualty check logic", () => {
  it("reads defaults and persists filters in the query string", () => {
    expect(filtersFromSearch("")).toEqual({ status: "open", reason: undefined, dateFrom: undefined, dateTo: undefined, q: undefined });
    const filters = filtersFromSearch("?status=resolved&reason=count_missing&date_from=2026-01-01&date_to=2026-01-31&q=Tyre");
    expect(filtersToSearch(filters).toString()).toBe("status=resolved&reason=count_missing&date_from=2026-01-01&date_to=2026-01-31&q=Tyre");
  });

  it("calculates allocation totals and detects an over-allocation", () => {
    const values = { a: { deaths: "2", injuries: "" }, b: { deaths: "3", injuries: "4" } };
    expect(assignedTotal(values, "deaths")).toBe(5);
    expect(assignedTotal(values, "injuries")).toBe(4);
    expect(isOverTotal(values, "deaths", 4)).toBe(true);
    expect(isOverTotal(values, "deaths", 5)).toBe(false);
    expect(canSubmitResolution(false, 2, true)).toBe(false);
  });

  it("allows confirm unknown without numeric entries", () => {
    expect(canSubmitResolution(true, 0, false)).toBe(true);
    expect(canSubmitResolution(false, 0, false)).toBe(false);
  });

  it("requires a dismissal reason of at least three characters", () => {
    expect(dismissReasonError("no")).toBe("Enter at least 3 characters.");
    expect(dismissReasonError("duplicate")).toBeUndefined();
  });

  it("maps API validation errors", () => {
    expect(mapApiError({ response: { data: { detail: [{ msg: "Value error, Provide at least one entry" }] } } })).toBe("Provide at least one entry");
    expect(mapApiError({ response: { data: { detail: "Assigned deaths exceeds total" } } })).toBe("Assigned deaths exceeds total");
  });

  it("builds partial entries with per-type unknown markers", () => {
    expect(buildResolutionEntries(
      { tyre: { deaths: "2" }, beirut: {} },
      { tyre: { injuries: true }, beirut: { deaths: true } },
    )).toEqual([
      { incident_id: "tyre", deaths: 2, unknown_injuries: true },
      { incident_id: "beirut", unknown_deaths: true },
    ]);
  });

  it("maps structured validation errors to incident fields and summary", () => {
    const mapped = mapFieldErrors({ response: { data: { errors: [
      { incident_id: "tyre", field: "deaths", code: "over_total", message: "Too many deaths." },
      { incident_id: null, field: "entries", code: "required", message: "Add an entry." },
    ] } } });
    expect(mapped.fields).toEqual({ "tyre.deaths": "Too many deaths." });
    expect(mapped.summary).toEqual(["Add an entry."]);
  });
});
