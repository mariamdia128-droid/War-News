import { useQuery } from "@tanstack/react-query";
import { liveListQueryOptions } from "../../lib/liveListPolling";
import { getAirViolationWindows, getAirViolations, getAirViolationSummary } from "./api";
import type { AirViolationFilters } from "./types";

export const airViolationKeys = {
  list: (filters: AirViolationFilters) => ["air-violations", filters] as const,
  windows: (filters: AirViolationFilters) => ["air-violations", "windows", filters] as const,
  summary: (filters: AirViolationFilters) => ["air-violations", "summary", filters] as const,
};

export const useAirViolationsQuery = (filters: AirViolationFilters, live = true) =>
  useQuery({
    queryKey: airViolationKeys.list(filters),
    queryFn: () => getAirViolations(filters),
    ...(live ? liveListQueryOptions : {}),
    refetchInterval: live ? 5_000 : false,
    refetchIntervalInBackground: live,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

export const useAirViolationSummaryQuery = (filters: AirViolationFilters, live = true) =>
  useQuery({
    queryKey: airViolationKeys.summary(filters),
    queryFn: () => getAirViolationSummary(filters),
    ...(live ? liveListQueryOptions : {}),
    refetchInterval: live ? 30_000 : false,
    refetchIntervalInBackground: live,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

export const useAirViolationWindowsQuery = (filters: AirViolationFilters, live = true) =>
  useQuery({
    queryKey: airViolationKeys.windows(filters),
    queryFn: () => getAirViolationWindows(filters),
    ...(live ? liveListQueryOptions : {}),
    refetchInterval: live ? 5_000 : false,
    refetchIntervalInBackground: live,
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });
