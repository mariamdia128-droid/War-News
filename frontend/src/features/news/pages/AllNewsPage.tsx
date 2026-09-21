import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "../../../components/StatusBadge";
import { Button, DataTable, EmptyState, Input, Label, Select, type DataTableColumn } from "../../../components/ui";
import { formatDateTime } from "../../../lib/formatters";
import { getBeirutDate } from "../../../lib/localDate";
import { getFilteredNews } from "../api";
import type { FilteredNewsItem } from "../types";

const PAGE_SIZE = 100;
const DEFAULT_EVENT_DATE_FROM = "2026-08-01";

const twoLineClampClass =
  "overflow-hidden text-ellipsis [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:3]";

const statusVariant = (status: string) => {
  if (status === "materialized") return "success" as const;
  if (status === "duplicate") return "neutral" as const;
  if (status === "error") return "danger" as const;
  return "accent" as const;
};

const eventDay = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Beirut",
    month: "short",
    day: "2-digit",
    year: "numeric",
  }).format(new Date(value));

const eventHour = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Beirut",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date(value));

export const AllNewsPage = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [eventDateFrom, setEventDateFrom] = useState(DEFAULT_EVENT_DATE_FROM);
  const [eventDateTo, setEventDateTo] = useState(getBeirutDate());
  const [sourceName, setSourceName] = useState("");
  const [status, setStatus] = useState("");
  const [relatedOnly, setRelatedOnly] = useState(false);
  const [search, setSearch] = useState("");
  const offset = (page - 1) * PAGE_SIZE;

  const filters = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset,
      eventDateFrom: eventDateFrom || undefined,
      eventDateTo: eventDateTo || undefined,
      sourceName: sourceName || undefined,
      status: status || undefined,
      relatedOnly,
      search: search || undefined,
    }),
    [eventDateFrom, eventDateTo, offset, relatedOnly, search, sourceName, status],
  );

  const query = useQuery({
    queryKey: ["filtered-news", filters],
    queryFn: () => getFilteredNews(filters),
  });

  const rows = query.data?.items ?? [];
  const total = query.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const sourceOptions = useMemo(() => {
    const names = new Set(rows.map((row) => row.source_name).filter(Boolean) as string[]);
    return [...names].sort().map((name) => ({ value: name, label: name }));
  }, [rows]);

  const columns: Array<DataTableColumn<FilteredNewsItem>> = [
    {
      key: "index",
      header: "#",
      headerClassName: "w-12 whitespace-nowrap",
      cellClassName: "w-12 tabular-nums text-text-muted",
      render: (row) => offset + rows.indexOf(row) + 1,
    },
    {
      key: "time",
      header: "Event Day / Hour",
      headerClassName: "w-[12rem] whitespace-nowrap",
      cellClassName: "w-[12rem]",
      render: (row) => (
        <div className="space-y-0.5">
          <p className="font-semibold text-text-primary">{eventDay(row.event_at)}</p>
          <p className="text-caption font-mono text-accent">{eventHour(row.event_at)}</p>
        </div>
      ),
    },
    {
      key: "report",
      header: "Filtered News (Khabar)",
      headerClassName: "min-w-[24rem]",
      cellClassName: "min-w-[24rem]",
      render: (row) => (
        <div className="space-y-1.5">
          <p className={`${twoLineClampClass} whitespace-normal leading-6 text-text-primary`} dir="auto">
            {row.khabar}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-caption text-text-muted">
            <span>Raw #{row.id}</span>
            {row.external_message_id ? <span>· ID: {row.external_message_id}</span> : null}
            {row.source_name ? (
              <span className="rounded bg-surface-subtle px-1.5 py-0.5 font-medium text-text-secondary">
                {row.source_name}
              </span>
            ) : null}
          </div>
        </div>
      ),
    },
    {
      key: "incident_link",
      header: "Related Incident",
      headerClassName: "w-[16rem]",
      cellClassName: "w-[16rem]",
      render: (row) => {
        if (!row.incident_id) {
          return (
            <span className="inline-flex items-center rounded-md bg-surface-subtle px-2.5 py-1 text-caption text-text-muted">
              No incident linked
            </span>
          );
        }
        return (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
              <span className="font-medium text-text-primary text-small">Incident linked</span>
            </div>
            {row.village_name || row.condition_name ? (
              <p className="text-caption text-text-secondary">
                {row.village_name ? <span>📍 {row.village_name} </span> : null}
                {row.condition_name ? <span>⚡ {row.condition_name}</span> : null}
              </p>
            ) : null}
          </div>
        );
      },
    },
    {
      key: "status",
      header: "Pipeline Status",
      headerClassName: "w-[10rem]",
      cellClassName: "w-[10rem]",
      render: (row) => (
        <StatusBadge label={row.status} variant={statusVariant(row.status)} />
      ),
    },
    {
      key: "reason",
      header: "Relevance Reason",
      headerClassName: "w-[16rem]",
      cellClassName: "w-[16rem]",
      render: (row) => (
        <p className={`${twoLineClampClass} text-small leading-5 text-text-muted`}>
          {row.reasoning ?? (row.verdict === "relevant" ? "Classified as relevant" : "Relevant incident news")}
        </p>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-1">
          <h1 className="text-h3 font-semibold text-text-primary">Filtered News</h1>
          <p className="max-w-3xl text-small leading-6 text-text-muted">
            All filtered news saved in the database, ordered chronologically day by day and hour by hour with direct linkage to incidents.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant={relatedOnly ? "primary" : "secondary"}
            onClick={() => {
              setRelatedOnly(!relatedOnly);
              setPage(1);
            }}
          >
            {relatedOnly ? "Showing: Related to Incidents only" : "Filter: Related to Incidents"}
          </Button>
        </div>
      </section>

      <section className="grid gap-4 rounded-lg border border-border bg-surface-raised p-4 shadow-[0_1px_2px_rgba(11,34,54,0.04)] md:grid-cols-5">
        <div className="space-y-2">
          <Label htmlFor="filtered-from">From Date</Label>
          <Input id="filtered-from" type="date" value={eventDateFrom} onChange={(event) => {
            setEventDateFrom(event.target.value);
            setPage(1);
          }} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="filtered-to">To Date</Label>
          <Input id="filtered-to" type="date" value={eventDateTo} onChange={(event) => {
            setEventDateTo(event.target.value);
            setPage(1);
          }} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="filtered-source">Source</Label>
          <Select
            id="filtered-source"
            value={sourceName}
            placeholder="All sources"
            options={sourceOptions}
            onChange={(value) => {
              setSourceName(value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="filtered-status">Status</Label>
          <Select
            id="filtered-status"
            value={status}
            placeholder="All statuses"
            options={[
              { value: "parsed", label: "Parsed" },
              { value: "materialized", label: "Materialized" },
              { value: "duplicate", label: "Duplicate" },
              { value: "error", label: "Error" },
            ]}
            onChange={(value) => {
              setStatus(value);
              setPage(1);
            }}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="filtered-search">Search</Label>
          <Input id="filtered-search" value={search} placeholder="Text, village, or ID" onChange={(event) => {
            setSearch(event.target.value);
            setPage(1);
          }} />
        </div>
      </section>

      <DataTable
        columns={columns}
        rows={rows}
        getRowKey={(row) => String(row.id)}
        minWidth="1180px"
        clientSort={false}
        loading={query.isLoading}
        error={query.isError}
        emptyState={<EmptyState title="No filtered news found" description="Try adjusting your date range or filters." />}
        errorState={<EmptyState title="Could not load filtered news" description="Check API connection and try again." />}
        actions={(row) => (
          <Button
            type="button"
            variant="secondary"
            disabled={!row.incident_id}
            onClick={() => {
              if (row.incident_id) navigate(`../incidents/${row.incident_id}`);
            }}
          >
            Open incident
          </Button>
        )}
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-small text-text-muted">
          Showing {rows.length} of {total} filtered news items · Page {page} of {totalPages}
        </p>
        <div className="flex gap-2">
          <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
          <Button variant="secondary" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next</Button>
        </div>
      </div>

      <p className="text-caption text-text-muted">
        Last loaded at {formatDateTime(new Date())}.
      </p>
    </div>
  );
};
