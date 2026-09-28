import { useContext, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ShellContext } from "../../../app/AppShell";
import { Button, Dialog, Input } from "../../../components/ui";
import { formatDate, formatDateTime } from "../../../lib/formatters";
import { roleBaseFromPath } from "../../../lib/rolePath";
import { getIncidentCasualtyFlags } from "../api";
import { assignedTotal, buildResolutionEntries, canSubmitResolution, dismissReasonError, isWholeNonNegative, mapApiError, mapFieldErrors, unresolvedSiblingIds, type AllocationValues } from "../logic";
import { useCasualtyFlag, useDismissCasualtyFlag, useResolveCasualtyFlag } from "../hooks";
import type { CasualtyFlagDetail, CasualtyKind } from "../types";

const kinds: CasualtyKind[] = ["deaths", "injuries"];
const label = (kind: CasualtyKind) => kind === "deaths" ? "Deaths" : "Injuries";

const Evidence = ({ text, evidence }: { text: string; evidence: string | null }) => {
  if (!evidence || !text.includes(evidence)) return <>{text}</>;
  const [before, ...after] = text.split(evidence);
  return <>{before}<mark className="rounded bg-warning/20 px-1 text-inherit">{evidence}</mark>{after.join(evidence)}</>;
};

const ReadOnlyResolution = ({ flag }: { flag: CasualtyFlagDetail }) => (
  <section className="rounded-lg border border-border bg-surface-muted p-4">
    <h3 className="font-semibold text-text-primary">This check is {flag.status.replace("_", " ")}</h3>
    {flag.resolved_at ? <p className="mt-1 text-small text-text-muted">By {flag.resolved_by ?? "an administrator"} on {formatDateTime(flag.resolved_at)}</p> : null}
    {flag.resolution?.entries?.length ? <ul className="mt-3 space-y-1 text-small">{flag.resolution.entries.map((entry) => <li key={entry.incident_id}>{entry.incident_id}: {entry.deaths === undefined ? "" : `${entry.deaths} deaths`} {entry.injuries === undefined ? "" : `${entry.injuries} injuries`}</li>)}</ul> : null}
    {flag.resolution?.confirmed_unknown ? <p className="mt-2 text-small">Confirmed unknown</p> : null}
    {flag.resolution?.note ? <p className="mt-2 text-small">Note: {flag.resolution.note}</p> : null}
    {flag.resolution?.dismiss_reason ? <p className="mt-2 text-small">Dismissed because: {flag.resolution.dismiss_reason}</p> : null}
    {flag.auto_clear_reason ? <p className="mt-2 text-small">Auto-cleared because: {flag.auto_clear_reason}</p> : null}
  </section>
);

export const CasualtyCheckPanel = ({ id: initialId, onClose, onComplete, inline = false }: { id: string; onClose: () => void; onComplete: () => void; inline?: boolean }) => {
  const location = useLocation();
  const shell = useContext(ShellContext);
  // After a partial aggregate save the panel moves on to an open sibling flag.
  const [id, setId] = useState(initialId);
  useEffect(() => setId(initialId), [initialId]);
  const query = useCasualtyFlag(id);
  const resolve = useResolveCasualtyFlag();
  const dismiss = useDismissCasualtyFlag();
  const [values, setValues] = useState<AllocationValues>({});
  const [unknown, setUnknown] = useState(false);
  const [unknownRows, setUnknownRows] = useState<Record<string, Partial<Record<CasualtyKind, boolean>>>>({});
  const [note, setNote] = useState("");
  const [showDismiss, setShowDismiss] = useState(false);
  const [dismissReason, setDismissReason] = useState("");
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [saveResult, setSaveResult] = useState("");
  const [serverRemaining, setServerRemaining] = useState<Partial<Record<CasualtyKind, number>>>({});

  useEffect(() => { setValues({}); setUnknown(false); setUnknownRows({}); setNote(""); setError(""); setFieldErrors({}); setServerRemaining({}); }, [id]);
  useEffect(() => setSaveResult(""), [initialId]);
  const nextOpenSiblingFlag = async (siblingIds: string[]) => {
    for (const incidentId of siblingIds) {
      const open = (await getIncidentCasualtyFlags(incidentId)).find((item) => item.reason_code === flag?.reason_code);
      if (open) return open.id;
    }
    return null;
  };
  const flag = query.data;
  const totals = flag?.detail.bulletin_totals ?? {};
  const baseAssigned = (kind: CasualtyKind) => typeof totals[kind] === "number" ? totals[kind] - (serverRemaining[kind] ?? flag?.detail.remaining_total?.[kind] ?? totals[kind]) : 0;
  const over = useMemo(() => kinds.some((kind) => typeof totals[kind] === "number" && baseAssigned(kind) + assignedTotal(values, kind) > (totals[kind] as number)), [flag?.detail.remaining_total, serverRemaining, totals, values]);
  const setValue = (incidentId: string, kind: CasualtyKind, value: string) => {
    if (!isWholeNonNegative(value)) return;
    setValues((current) => ({ ...current, [incidentId]: { ...current[incidentId], [kind]: value } }));
  };
  const setUnknownValue = (incidentId: string, kind: CasualtyKind, checked: boolean) => {
    setUnknownRows((current) => ({ ...current, [incidentId]: { ...current[incidentId], [kind]: checked } }));
    if (checked) setValue(incidentId, kind, "");
  };
  const effectiveUnknown = flag?.reason_code === "count_missing" && unknown
    ? { [flag.incident_id]: Object.fromEntries(flag.affected_types.map((kind) => [kind, true])) }
    : unknownRows;
  const entries = buildResolutionEntries(values, effectiveUnknown);
  const unknownLocationCount = Object.values(effectiveUnknown).filter((row) => Object.values(row).some(Boolean)).length;
  const canSubmit = Boolean(flag) && !resolve.isPending && canSubmitResolution(unknown, entries.length, over, unknownLocationCount);

  const submit = async () => {
    if (!flag || !canSubmit) return;
    setError("");
    setFieldErrors({});
    try {
      const response = await resolve.mutateAsync({ id, entries, note: note.trim() || undefined });
      const resolvedNames = response.results.filter((item) => item.resolved).map((item) => flag.incidents.find((incident) => incident.id === item.incident_id)?.village_name ?? item.incident_id);
      const openNames = response.results.filter((item) => item.still_open).map((item) => flag.incidents.find((incident) => incident.id === item.incident_id)?.village_name ?? item.incident_id);
      setSaveResult([resolvedNames.length ? `Resolved: ${resolvedNames.join(", ")}.` : "", openNames.length ? `Still open: ${openNames.join(", ")}.` : ""].filter(Boolean).join(" "));
      setServerRemaining(response.remaining_total);
      setValues({}); setUnknown(false); setUnknownRows({});
      shell?.showToast("Casualty check saved.");
      if (response.results.some((item) => item.still_open)) { await query.refetch(); return; }
      const nextId = flag.reason_code === "aggregate_no_breakdown"
        ? await nextOpenSiblingFlag(unresolvedSiblingIds(flag.incidents.map((incident) => incident.id), response.results))
        : null;
      if (nextId === id) await query.refetch();
      else if (nextId) setId(nextId);
      else onComplete();
    } catch (requestError) { const mapped = mapFieldErrors(requestError); setFieldErrors(mapped.fields); setError(mapped.summary.join(" ") || mapApiError(requestError)); }
  };

  const content = <>
    {query.isLoading ? <div className="space-y-3" aria-label="Loading casualty check"><div className="h-24 animate-pulse rounded bg-surface-muted" /><div className="h-48 animate-pulse rounded bg-surface-muted" /></div> : query.isError || !flag ? <div role="alert"><p className="text-danger">Could not load this casualty check.</p><Button className="mt-4" variant="secondary" onClick={() => query.refetch()}>Try again</Button></div> : <div className="space-y-6">
      <section><div className="flex flex-wrap justify-between gap-2 text-small text-text-muted"><span>{flag.source_name ?? "Unknown source"}</span><span>{flag.event_date ? formatDate(flag.event_date) : "Unknown date"}</span></div><p dir="rtl" lang="ar" className="mt-3 rounded-lg border border-border bg-surface p-4 text-right text-body leading-8 text-text-primary"><Evidence text={flag.message_text ?? flag.evidence_sentence ?? "No original message available."} evidence={flag.evidence_sentence} /></p>{flag.message_snapshot_used ? <p className="mt-2 text-small text-text-muted">Original raw message is unavailable; showing the saved flag snapshot.</p> : null}<Link className="mt-3 inline-block text-small font-semibold text-accent" to={`${roleBaseFromPath(location.pathname)}/incidents/${flag.incident_id}`}>Open incident</Link></section>
      <section><h3 className="font-semibold text-text-primary">What we know</h3><div className="mt-3 space-y-2">{flag.incidents.map((incident) => <div key={incident.id} className="grid grid-cols-3 gap-2 rounded border border-border p-3 text-small"><span>{incident.village_name ?? "Unknown location"}</span><span>Deaths: {incident.deaths ?? "Unknown"}</span><span>Injuries: {incident.injuries ?? "Unknown"}</span></div>)}</div>{kinds.map((kind) => totals[kind] != null || flag.detail.remaining_total?.[kind] != null ? <p key={kind} className="mt-2 text-small text-text-muted">{label(kind)} — bulletin total: {totals[kind] ?? "Unknown"}; remaining: {serverRemaining[kind] ?? flag.detail.remaining_total?.[kind] ?? "Unknown"}</p> : null)}</section>
      {flag.status !== "open" ? <ReadOnlyResolution flag={flag} /> : <form onSubmit={(event) => { event.preventDefault(); void submit(); }} className="space-y-5">
        {flag.reason_code === "count_missing" ? <><label className="flex items-center gap-2 text-small font-semibold"><input type="checkbox" checked={unknown} onChange={(event) => setUnknown(event.target.checked)} />Confirm unknown</label><div className="grid gap-4 sm:grid-cols-2">{flag.affected_types.map((kind, index) => <label key={kind} className="text-small font-semibold">{label(kind as CasualtyKind)}<Input autoFocus={index === 0} className="mt-1" type="number" inputMode="numeric" min="0" step="1" disabled={unknown} value={values[flag.incident_id]?.[kind as CasualtyKind] ?? ""} onChange={(event) => setValue(flag.incident_id, kind as CasualtyKind, event.target.value)} />{fieldErrors[`${flag.incident_id}.${kind}`] ? <span className="mt-1 block text-danger">{fieldErrors[`${flag.incident_id}.${kind}`]}</span> : null}</label>)}</div></> : <div className="space-y-4">{flag.incidents.map((incident, rowIndex) => <fieldset key={incident.id} className="rounded-lg border border-border p-4"><legend className="px-1 font-semibold">{incident.village_name ?? "Unknown location"}</legend><div className="grid grid-cols-2 gap-3">{kinds.map((kind) => <div key={kind}><label className="text-small font-semibold">{label(kind)}<Input autoFocus={rowIndex === 0 && kind === "deaths"} className="mt-1" type="number" inputMode="numeric" min="0" step="1" disabled={Boolean(unknownRows[incident.id]?.[kind])} value={values[incident.id]?.[kind] ?? ""} onChange={(event) => setValue(incident.id, kind, event.target.value)} /></label><label className="mt-2 flex items-center gap-2 text-small"><input type="checkbox" checked={Boolean(unknownRows[incident.id]?.[kind])} onChange={(event) => setUnknownValue(incident.id, kind, event.target.checked)} />Confirm unknown</label>{fieldErrors[`${incident.id}.${kind}`] ? <span className="mt-1 block text-small text-danger">{fieldErrors[`${incident.id}.${kind}`]}</span> : null}</div>)}</div></fieldset>)}<div className="grid grid-cols-2 gap-3">{kinds.map((kind) => <p key={kind} className="text-small font-semibold">{label(kind)}: assigned {baseAssigned(kind) + assignedTotal(values, kind)} of {totals[kind] ?? "unknown"}</p>)}</div>{over ? <p className="text-small font-semibold text-danger" role="alert">Assigned values cannot exceed the bulletin total.</p> : null}</div>}
        <label className="block text-small font-semibold">Optional note<textarea className="mt-1 min-h-24 w-full rounded-md border border-input-border p-3 font-normal" value={note} onChange={(event) => setNote(event.target.value)} /></label>
        {error ? <p className="text-small font-semibold text-danger" role="alert">{error}</p> : null}
        {saveResult ? <p className="text-small font-semibold text-success" role="status">{saveResult}</p> : null}
        <div className="flex flex-wrap justify-between gap-3 border-t border-border pt-4"><Button type="button" variant="destructive" onClick={() => setShowDismiss(true)}>Dismiss</Button><Button type="submit" disabled={!canSubmit} isLoading={resolve.isPending} loadingText="Saving…">Save entered values</Button></div>
      </form>}
      {showDismiss ? <div className="rounded-lg border border-danger/30 bg-surface p-4"><label className="text-small font-semibold">Dismiss reason<Input autoFocus className="mt-1" value={dismissReason} onChange={(event) => setDismissReason(event.target.value)} /></label>{dismiss.isError ? <p className="mt-2 text-small text-danger">{mapApiError(dismiss.error)}</p> : null}<div className="mt-3 flex justify-end gap-2"><Button variant="secondary" onClick={() => setShowDismiss(false)}>Cancel</Button><Button variant="destructive" disabled={Boolean(dismissReasonError(dismissReason))} isLoading={dismiss.isPending} onClick={async () => { const reasonError = dismissReasonError(dismissReason); if (reasonError) { setError(reasonError); return; } await dismiss.mutateAsync({ id, reason: dismissReason.trim() }); shell?.showToast("Casualty check dismissed."); onComplete(); }}>Dismiss</Button></div></div> : null}
    </div>}
  </>;
  return inline ? (
    <section className="rounded-lg border border-warning/40 bg-warning/5 p-5 sm:p-6">
      <p className="mb-4 text-caption font-semibold uppercase tracking-wide text-warning">Casualty check</p>
      {content}
    </section>
  ) : (
    <Dialog title="Casualty check" eyebrow={flag ? (flag.reason_code === "count_missing" ? "Missing number" : "Aggregate toll") : "Loading"} onClose={onClose} size="panel">{content}</Dialog>
  );
};
