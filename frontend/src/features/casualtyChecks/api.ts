import { apiClient } from "../../lib/apiClient";
import type { CasualtyFlagDetail, IncidentCasualtyFlag, ResolveCasualtyFlagPayload, ResolveCasualtyFlagResponse } from "./types";

export const getCasualtyFlag = async (id: string) => (await apiClient.get<CasualtyFlagDetail>(`/verification-flags/${id}`)).data;
export const resolveCasualtyFlag = async ({ id, ...payload }: ResolveCasualtyFlagPayload) => (await apiClient.post<ResolveCasualtyFlagResponse>(`/verification-flags/${id}/resolve`, payload)).data;
export const dismissCasualtyFlag = async ({ id, reason }: { id: string; reason: string }) => (await apiClient.post(`/verification-flags/${id}/dismiss`, { reason })).data;
export const getIncidentCasualtyFlags = async (incidentId: string) => (await apiClient.get<IncidentCasualtyFlag[]>(`/incidents/${incidentId}/verification-flags`)).data;
