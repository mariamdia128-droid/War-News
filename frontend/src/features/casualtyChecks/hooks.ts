import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { dismissCasualtyFlag, getCasualtyFlag, getIncidentCasualtyFlags, resolveCasualtyFlag } from "./api";

export const casualtyFlagKeys = { all: ["casualty-flags"] as const, detail: (id: string) => ["casualty-flags", "detail", id] as const };

export const useCasualtyFlag = (id?: string) => useQuery({ queryKey: casualtyFlagKeys.detail(id ?? ""), queryFn: () => getCasualtyFlag(id as string), enabled: Boolean(id) });
const useFlagMutation = <T, TResult>(mutationFn: (value: T) => Promise<TResult>) => { const client = useQueryClient(); return useMutation({ mutationFn, onSuccess: async () => { await client.invalidateQueries({ queryKey: casualtyFlagKeys.all }); await client.invalidateQueries({ queryKey: ["incidents"] }); await client.invalidateQueries({ queryKey: ["incident"] }); } }); };
export const useResolveCasualtyFlag = () => useFlagMutation(resolveCasualtyFlag);
export const useDismissCasualtyFlag = () => useFlagMutation(dismissCasualtyFlag);
export const useIncidentCasualtyFlags = (incidentId?: string) => useQuery({ queryKey: ["incidents", "verification-flags", incidentId], queryFn: () => getIncidentCasualtyFlags(incidentId as string), enabled: Boolean(incidentId) });
