import { StatusBadge } from "../../../components/StatusBadge";
import type { IncidentDetail } from "../types";

type VillageMatchNoticeProps = Pick<
  IncidentDetail,
  | "village_review_required"
  | "any_village_low_confidence"
  | "resolved_by_geo_context"
  | "geo_context_anchor_village_name"
  | "geo_context_distance_meters"
  | "normalized_from"
  | "alternate_candidate_village_name"
>;

const formatDistanceKm = (meters?: number | null) =>
  typeof meters === "number" ? `${(meters / 1000).toFixed(1)} km` : null;

export const VillageMatchNotice = ({
  village_review_required,
  any_village_low_confidence,
  resolved_by_geo_context,
  geo_context_anchor_village_name,
  geo_context_distance_meters,
  normalized_from,
  alternate_candidate_village_name,
}: VillageMatchNoticeProps) => {
  const distance = formatDistanceKm(geo_context_distance_meters);
  if (resolved_by_geo_context) {
    return (
      <div className="mt-4 rounded-md border border-accent bg-surface p-3">
        <StatusBadge label="Nearby-location match" variant="success" />
        <p className="mt-2 text-small text-text-muted">
          Village resolved from nearby location
          {geo_context_anchor_village_name
            ? ` (${geo_context_anchor_village_name})`
            : ""}
          {distance ? `, ${distance}` : ""}
          .
        </p>
      </div>
    );
  }

  if (normalized_from) {
    return (
      <div className="mt-4 rounded-md border border-accent bg-surface p-3">
        <StatusBadge label="Normalized village" variant="success" />
        <p className="mt-2 text-small text-text-muted">
          Village resolved from “{normalized_from}”.
        </p>
      </div>
    );
  }

  if (!village_review_required && !any_village_low_confidence) {
    return null;
  }

  return (
    <div className="mt-4 rounded-md border border-warning bg-surface p-3">
      <StatusBadge label="Village match uncertain" variant="warning" />
      <p className="mt-2 text-small text-text-muted">
        Village match uncertain
        {alternate_candidate_village_name
          ? ` — also possible: ${alternate_candidate_village_name}`
          : ""}
        .
      </p>
    </div>
  );
};
