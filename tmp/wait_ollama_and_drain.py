"""Poll Ollama, then enqueue pipeline sweeps until Sep 10 incidents exist."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.news.services.pipeline.pipeline_jobs import enqueue_pipeline_sweep

POLL_SECONDS = 10
MAX_WAIT_SECONDS = 30 * 60
TARGET_DAY = "2026-09-10"


def ollama_up() -> bool:
    base = settings.ollama_base_url.rstrip("/")
    try:
        response = httpx.get(f"{base}/api/tags", timeout=5.0)
        return response.status_code < 500
    except Exception as exc:  # noqa: BLE001
        print(f"ollama down: {type(exc).__name__}: {exc}", flush=True)
        return False


def sep10_stats(db) -> dict[str, int]:
    row = db.execute(
        text(
            """
            SELECT
              COUNT(*) FILTER (
                WHERE status = 'parsed' AND extraction_result IS NULL
              ) AS parsed_no_ext,
              COUNT(*) FILTER (WHERE status = 'error') AS errors,
              COUNT(*) FILTER (WHERE status = 'materialized') AS materialized_msgs,
              (
                SELECT COUNT(*)
                FROM incidents i
                WHERE i.is_deleted = false
                  AND i.event_date = CAST(:day AS date)
              ) AS incidents
            FROM raw_messages
            WHERE DATE(
              COALESCE(message_datetime, received_at) AT TIME ZONE 'Asia/Beirut'
            ) = CAST(:day AS date)
            """
        ),
        {"day": TARGET_DAY},
    ).mappings().one()
    return dict(row)


def main() -> int:
    print(f"waiting for Ollama at {settings.ollama_base_url}", flush=True)
    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        if ollama_up():
            print("ollama reachable", flush=True)
            break
        time.sleep(POLL_SECONDS)
    else:
        print("gave up waiting for Ollama", flush=True)
        return 1

    sweeps = 0
    while time.time() < deadline:
        with SessionLocal() as db:
            stats = sep10_stats(db)
            print(f"sep10={stats}", flush=True)
            if stats["incidents"] > 0 and stats["parsed_no_ext"] == 0:
                print("done: Sep 10 incidents present and backlog clear", flush=True)
                return 0
            job_id = enqueue_pipeline_sweep(db)
            sweeps += 1
            print(f"enqueued sweep job_id={job_id} sweeps={sweeps}", flush=True)
        time.sleep(30)

    print("timed out before Sep 10 fully drained", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
