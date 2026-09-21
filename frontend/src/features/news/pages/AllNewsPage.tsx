import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { StatusBadge } from "../../../components/StatusBadge";
import { Button, DataTable, EmptyState, Input, Label, Select, type DataTableColumn } from "../../../components/ui";
import { formatDateTime } from "../../../lib/formatters";
import { getBeirutDate } from "../../../lib/localDate";
import { getFilteredNews } from "../api";
import type { FilteredNewsItem } from "../types";

const PAGE_SIZE = 150;
const DEFAULT_EVENT_DATE_FROM = "2026-08-20";

const twoLineClampClass =
  "overflow-hidden text-ellipsis [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2]";

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
    hour12: false,
  }).format(new Date(value));

export const AllNewsPage = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [eventDateFrom, setEventDateFrom] = useState(DEFAULT_EVENT_DATE_FROM);
  const [eventDateTo, setEventDateTo] = useState(getBeirutDate());
  const [sourceName, setSourceName] = useState("");
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const offset = (page - 1) * PAGE_SIZE;

  const filters = useMemo(
    () => ({
      limit: PAGE_SIZE,
      offset,
      eventDateFrom,
      eventDateTo,
      sourceName: sourceName || undefined,
      status: status || undefined,
      search: search || undefined,
    }),
    [eventDateFrom, eventDateTo, offset, search, sourceName, status],
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
      headerClassName: "w-14 whitespace-nowrap",
      cellClassName: "w-14 tabular-nums text-text-muted",
      render: (row) => offset + rows.indexOf(row) + 1,
    },
    {
      key: "time",
      header: "Day / hour",
      headerClassName: "w-[12rem] whitespace-nowrap",
      cellClassName: "w-[12rem]",
      render: (row) => (
        <div className="space-y-1">
          <p className="font-semibold text-text-primary">{eventDay(row.event_at)}</p>
          <p className="text-caption text-text-muted">{eventHour(row.event_at)}</p>
        </div>
      ),
    },
    {
      key: "report",
      header: "Filtered news",
      headerClassName: "min-w-[28rem]",
      cellClassName: "min-w-[28rem]",
      render: (row) => (
        <div className="space-y-1.5">
          <p className={`${twoLineClampClass} whitespace-normal leading-6 text-text-primary`} dir="auto">
            {row.khabar}
          </p>
          <p className="text-caption text-text-muted">
            Raw #{row.id}{row.external_message_id ? ` · ${row.external_message_id}` : ""}
          </p>
        </div>
      ),
    },
    {
      key: "source",
      header: "Source",
      headerClassName: "w-[11rem]",
      cellClassName: "w-[11rem]",
      render: (row) => row.source_name ?? row.source_platform ?? "Unknown",
    },
    {
      key: "status",
      header: "Pipeline",
      headerClassName: "w-[11rem]",
      cellClassName: "w-[11rem]",
      render: (row) => (
        <div className="space-y-2">
          <StatusBadge label={row.status} variant={statusVariant(row.status)} />
          {row.incident_id ? (
            <p className="text-caption text-text-muted">Incident created</p>
          ) : (
            <p className="text-caption text-text-muted">No incident row</p>
          )}
        </div>
      ),
    },
    {
      key: "reason",
      header: "Filter reason",
      headerClassName: "w-[18rem]",
      cellClassName: "w-[18rem]",
      render: (row) => (
        <p className={`${twoLineClampClass} text-small leading-6 text-text-muted`}>
          {row.reasoning ?? "Relevant filtered news"}
        </p>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <section className="space-y-1">
        <h1 className="text-h3 font-semibold text-text-primary">Filtered news</h1>
        <p className="max-w-3xl text-small leading-6 text-text-muted">
          Relevant filtered news saved in the database, ordered one by one by event day and hour.
        </p>
      </section>

      <section className="grid gap-4 rounded-lg border border-border bg-surface-raised p-4 shadow-[0_1px_2px_rgba(11,34,54,0.04)] md:grid-cols-5">
        <div className="space-y-2">
          <Label htmlFor="filtered-from">From</Label>
          <Input id="filtered-from" type="date" value={eventDateFrom} onChange={(event) => {
            setEventDateFrom(event.target.value);
            setPage(1);
          }} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="filtered-to">To</Label>
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
          <Input id="filtered-search" value={search} placeholder="Text or source id" onChange={(event) => {
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
        emptyState={<EmptyState title="No filtered news" description="Relevant filtered news will appear here after the pipeline processes source messages." />}
        errorState={<EmptyState title="Could not load filtered news" description="Try again." />}
        actions={(row) => (
          <Button
            type="button"
            variant="secondary"
            disabled={!row.incident_id}
            onClick={() => {
              if (row.incident_id) navigate(`../incidents/${row.incident_id}`);
            }}
          >
            View incident
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
