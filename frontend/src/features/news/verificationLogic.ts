import type { Incident, IncidentFilters } from "./types";

export const verificationTypeFromSearch = (search: string): IncidentFilters["verificationType"] | undefined => {
  const value = new URLSearchParams(search).get("verification_type");
  return value === "duplicate" || value === "casualty_missing_number" || value === "casualty_aggregate_toll" ? value : undefined;
};

export const verificationTypeLabel = (type: Incident["verification_types"][number]) =>
  type === "duplicate" ? "Duplicate" : type === "casualty_missing_number" ? "Missing number" : "Aggregate toll";
