import type { IncidentFilters } from "./types";

type VerificationType = NonNullable<IncidentFilters["verificationType"]>;

export const verificationTypeFromSearch = (search: string): IncidentFilters["verificationType"] | undefined => {
  const value = new URLSearchParams(search).get("verification_type");
  return value === "duplicate" || value === "casualty_missing_number" || value === "casualty_aggregate_toll" ? value : undefined;
};

// Wide enough to include every flagged incident; the list filters on event_date.
export const ALL_DATES_RANGE = { from: "2000-01-01", to: "2100-12-31" } as const;

export const isVerificationView = (verificationStatus: string, verificationType: string) =>
  verificationStatus === "needs_verification" || Boolean(verificationType);

export const outsideRangeNotice = (count: number | undefined) =>
  count && count > 0
    ? `${count} more flagged incident${count === 1 ? "" : "s"} outside this date range`
    : null;

export const hasNonDefaultFilters = (
  values: Record<string, string | boolean>,
  eventDateFrom: string,
  eventDateTo: string,
  defaults: { from: string; to: string },
) =>
  Object.values(values).some(Boolean) || eventDateFrom !== defaults.from || eventDateTo !== defaults.to;

export const verificationTypeLabel =(type: VerificationType) =>
  type === "duplicate" ? "Duplicate" : type === "casualty_missing_number" ? "Missing number" : "Aggregate toll";
