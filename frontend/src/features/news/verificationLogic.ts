import type { IncidentFilters } from "./types";

type VerificationType = NonNullable<IncidentFilters["verificationType"]>;

export const verificationTypeFromSearch = (search: string): IncidentFilters["verificationType"] | undefined => {
  const value = new URLSearchParams(search).get("verification_type");
  return value === "duplicate" || value === "casualty_missing_number" || value === "casualty_aggregate_toll" ? value : undefined;
};

export const verificationTypeLabel = (type: VerificationType) =>
  type === "duplicate" ? "Duplicate" : type === "casualty_missing_number" ? "Missing number" : "Aggregate toll";
