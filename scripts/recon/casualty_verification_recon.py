"""READ-ONLY recon: casualty verification buckets (War News 2026).

SELECT statements only, inside a READ ONLY transaction that is rolled back.
Writes nothing to the database or disk; prints findings to stdout.

Run from the repo root (PowerShell):
    $OutputEncoding = New-Object System.Text.UTF8Encoding $false
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false
    Get-Content -Raw -Encoding UTF8 scripts/recon/casualty_verification_recon.py | docker compose exec -T backend python -

Optional env: RECON_EXAMPLES (examples per bucket, default 5).
"""
from __future__ import annotations

import os
import re
import statistics
from collections import Counter, defaultdict

import psycopg2
import psycopg2.extras

EXAMPLES = int(os.environ.get("RECON_EXAMPLES", "5"))

# --- Arabic regexes (applied to normalized text: hamza forms -> ا, tashkeel/tatweel removed)
PRE = "(^|[^[:alpha:]])(و|ف|ب|ل|ك)?(ال|لل)?"
END = "([^[:alpha:]]|$)"
KW_STRICT = (
    PRE
    + "(شهيد|شهيدا|شهيدة|شهيده|شهيدان|شهيدين|شهيدتان|شهيدتين|شهداء|شهيدات"
    "|قتيل|قتيلا|قتيلة|قتيلان|قتيلين|قتلى|جريح|جريحا|جريحة|جريحان|جريحين|جرحى|جريحات"
    "|مصاب|مصابا|مصابة|مصابان|مصابين|مصابون|مصابات|ضحايا|ضحية|استشهاد|استشهد|استشهدت|مقتل)"
    + END
)
KW_WEAK = PRE + "(اصابة|اصابه|اصابات|اصيب|اصيبت|اصيبوا)" + END
WEAK_FP = "اصابة مباشرة|اصابات مباشرة|اصابه مباشره|اصابة دقيقة|اصابة الهدف|اصيب (ال)?(مبنى|منزل|هدف)"
ZERO = (
    "(دون|بدون|من دون|لا|لم (تسجل|يسجل|تفد|يفد|يسفر|تسفر|تؤد|يؤد)[^.،]{0,20})\\s*"
    "(وقوع|سقوط|تسجيل|اي|أي)?\\s*(اصابات|اصابة|ضحايا|خسائر بشرية|اصابات بشرية|اصابات في الارواح)"
)
CAS_NOUN = "(شهيد|شهداء|شهيدا|شهيدة|جريح|جرحى|جريحا|قتيل|قتلى|قتيلا|مصاب|مصابين|مصابا|اصابات|اصابة|ضحايا|شخص|اشخاص|مواطن|مواطنين)"
NUM_TEXT = (
    "[0-9٠-٩]+\\s*(من\\s+)?(ال)?" + CAS_NOUN
    + "|(اصابة|استشهاد|مقتل|سقوط|ارتقاء|جرح|اصيب|استشهد|قتل)\\s+[0-9٠-٩]+"
    + "|(الشهداء|الجرحى|الضحايا|المصابين|القتلى|الحصيلة)[^.]{0,30}[0-9٠-٩]+"
)
WORDNUM = (
    "(اثنان|اثنين|ثلاثة|ثلاث|اربعة|اربع|خمسة|خمس|ستة|ست|سبعة|سبع|ثمانية|ثماني|تسعة|تسع|عشرة|عشر)"
    "\\s+(شهداء|جرحى|قتلى|مصابين|اصابات|ضحايا|شهيدات|جريحات|اشخاص|مواطنين)"
)
REVISION = (
    "حصيل[ةه]\\s+(ال)?(اولي[ةه]|مؤقت[ةه]|غير نهائي[ةه]|اولى)|المعلومات الاولية|معلومات اولية"
    "|ارتفاع\\s+(عدد|حصيلة|الحصيلة)|ارتفع(ت)?\\s+(عدد|حصيلة|الحصيلة)|تحديث\\s+(ال)?حصيلة"
    "|(مراجعة|تصحيح)\\s+(ال)?حصيلة|(ال)?حصيلة\\s+(ال)?نهائية"
)
CUMULATIVE = "منذ (بدء|بداية)|الحصيلة (الاجمالية|التراكمية)|حصيلة العدوان|الحصيلة الاجمالية"

# Python-side sub-types for bucket C (why no number was extracted).
C_SUBTYPES = (
    ("C1 singular/dual word implies an exact count",
     r"(?<![\w])(?:و|ف|ب)?(شهيد|شهيدا|شهيدة|شهيدان|شهيدين|شهيدتان|شهيدتين|قتيل|قتيلا|قتيلة|قتيلان|قتيلين"
     r"|جريح|جريحا|جريحة|جريحان|جريحين|جريحتان|جريحتين|مصابان|اصابتين|اصابتان)(?![\w])"),
    ("C2 vague quantifier (عشرات/عدد من/مئات/...)",
     r"عشرات|عدد من|عدد كبير|مئات|المئات|بضعة|العديد من|كثير من|اكثر من"),
    ("C3 named victim / obituary (الشهيد فلان، تنعى)",
     r"(?<![\w])(?:و|ف|ب|ل)?(?:ال|لل)(شهيد|شهيدة|شهيده)(?![\w])|تنعى|تنعي|تزف|نعت|ينعى"),
    ("C4 bare plural / verb without count (استشهاد وإصابة مواطنين، وقوع إصابات)",
     r"شهداء|جرحى|مصابين|اصابات|ضحايا|قتلى|استشهاد|استشهد|اصيب|اصابة|مقتل"),
)

BASE_CTE = """
WITH m AS (
  SELECT r.id, r.raw_text, r.message_datetime, r.status::text AS status,
         r.extraction_result AS x, r.duplicate_of_id,
         -- Normalize hamza/tashkeel, then drop the "صفحة الإعلامي الشهيد علي شعيب" source
         -- header: it names a page, not a casualty (464 messages carry it).
         regexp_replace(
           regexp_replace(translate(coalesce(r.raw_text, ''), 'أإآٱ', 'اااا'),
                          '[ً-ٰٟـ]', '', 'g'),
           'الشهيد\\s*علي\\s*شعيب', ' ', 'g') AS t
  FROM raw_messages r
  WHERE r.extraction_result IS NOT NULL
    AND (r.extraction_result->>'is_relevant')::boolean
),
inc AS (
  SELECT raw_message_id,
         count(*) AS n_inc,
         count(DISTINCT village_id) AS n_inc_v,
         min(event_date) AS event_date
  FROM incidents
  WHERE NOT is_deleted AND raw_message_id IS NOT NULL
  GROUP BY 1
),
f AS (
  SELECT m.id, m.raw_text, m.message_datetime, m.status, m.duplicate_of_id, m.t,
    m.x->>'casualty_scope' AS casualty_scope,
    m.x->>'casualty_scope_evidence' AS scope_evidence,
    (m.x->>'casualty_scope_needs_review')::boolean AS scope_needs_review,
    m.x ? 'village_roles' AND jsonb_typeof(m.x->'village_roles') = 'array' AS has_roles,
    (SELECT count(*) FROM jsonb_array_elements(
        CASE WHEN jsonb_typeof(m.x->'village_roles') = 'array' THEN m.x->'village_roles' ELSE '[]'::jsonb END) e
      WHERE coalesce(e->>'role', 'target') = 'target') AS n_targets,
    (SELECT count(*) FROM jsonb_array_elements(
        CASE WHEN jsonb_typeof(m.x->'village_roles') = 'array' THEN m.x->'village_roles' ELSE '[]'::jsonb END) e
      WHERE coalesce(e->>'role', 'target') = 'target'
        AND (e->>'deaths' IS NOT NULL OR e->>'injuries' IS NOT NULL)) AS n_targets_num,
    CASE WHEN jsonb_typeof(m.x->'village') = 'array' THEN jsonb_array_length(m.x->'village') ELSE 0 END AS n_village_list,
    (SELECT count(*) FROM jsonb_array_elements(
        CASE WHEN jsonb_typeof(m.x->'sub_events') = 'array' THEN m.x->'sub_events' ELSE '[]'::jsonb END) s
      WHERE (s->'casualties'->>'deaths' IS NOT NULL OR s->'casualties'->>'injuries' IS NOT NULL
          OR s->'casualties'->>'total_deaths' IS NOT NULL OR s->'casualties'->>'total_injuries' IS NOT NULL)) AS n_sub_num,
    (m.x->'casualties'->>'total_deaths')::int AS root_td,
    (m.x->'casualties'->>'total_injuries')::int AS root_ti,
    (m.x->'casualties'->>'deaths')::int AS root_d,
    (m.x->'casualties'->>'injuries')::int AS root_i,
    coalesce(inc.n_inc, 0) AS n_inc, coalesce(inc.n_inc_v, 0) AS n_inc_v, inc.event_date,
    m.t ~ %(kw_strict)s OR (m.t ~ %(kw_weak)s AND NOT m.t ~ %(weak_fp)s) AS cas_kw,
    m.t ~ %(kw_weak)s AND NOT m.t ~ %(kw_strict)s AS weak_only,
    m.t ~ %(zero)s AS zero_stmt,
    m.t ~ %(num_text)s AS num_text,
    m.t ~ %(wordnum)s AS wordnum_text,
    m.t ~ %(revision)s AS revision,
    m.t ~ %(cumulative)s AS cumulative
  FROM m LEFT JOIN inc ON inc.raw_message_id = m.id
),
g AS (
  SELECT f.*,
    coalesce(root_td, root_ti, root_d, root_i) IS NOT NULL OR n_targets_num > 0 OR n_sub_num > 0 AS has_num,
    (n_targets_num + n_sub_num) AS n_loc_num,
    greatest(CASE WHEN has_roles THEN n_targets ELSE n_village_list END, n_inc_v) AS n_loc
  FROM f
)
SELECT g.*,
  CASE
    WHEN n_loc >= 2 AND has_num AND n_loc_num >= 1 THEN 'B'
    WHEN n_loc >= 2 AND (has_num OR num_text) AND cas_kw THEN 'D'
    WHEN n_loc >= 2 AND has_num THEN 'D'
    WHEN has_num THEN 'A'
    WHEN cas_kw AND num_text THEN 'X'
    WHEN cas_kw AND NOT (zero_stmt AND weak_only) THEN 'C'
    WHEN zero_stmt THEN 'F0'
    ELSE 'F'
  END AS bucket
FROM g
"""

INCIDENTS_SQL = """
SELECT i.id::text AS id, i.raw_message_id, i.village_id, i.story_group_id::text AS story_group_id,
       coalesce(i.village_display_name, v.ref_name_ar, v.ref_name_en) AS village,
       i.event_date, i.created_at, i.deaths, i.injuries, i.total_deaths, i.total_injuries,
       i.verification_status, i.verification_reason, i.duplicate_flag
FROM incidents i LEFT JOIN villages v ON v.id = i.village_id
WHERE NOT i.is_deleted
"""

MERGE_FILL_SQL = """
SELECT u.incident_id::text AS incident_id, u.created_at, u.old_values, u.new_values
FROM incident_updates u
JOIN incidents i ON i.id = u.incident_id AND NOT i.is_deleted
WHERE u.action = 'pipeline_merge'
  AND (u.new_values ? 'deaths' OR u.new_values ? 'injuries'
       OR u.new_values ? 'total_deaths' OR u.new_values ? 'total_injuries')
"""

NULL_ZERO_SQL = """
SELECT col,
  count(*) FILTER (WHERE v IS NULL) AS n_null,
  count(*) FILTER (WHERE v = 0) AS n_zero,
  count(*) FILTER (WHERE v > 0) AS n_pos
FROM incidents i
CROSS JOIN LATERAL (VALUES ('deaths', i.deaths), ('injuries', i.injuries),
                           ('total_deaths', i.total_deaths), ('total_injuries', i.total_injuries)) AS c(col, v)
WHERE NOT i.is_deleted
GROUP BY col ORDER BY col
"""

COMBO_SQL = """
SELECT (deaths IS NULL) AS d_null, (total_deaths IS NULL) AS td_null,
       (deaths = 0) AS d_zero, (total_deaths = 0) AS td_zero, count(*)
FROM incidents WHERE NOT is_deleted GROUP BY 1,2,3,4 ORDER BY 5 DESC
"""

ROOT_ZERO_SQL = """
SELECT key, count(*) FILTER (WHERE val = 'null') AS n_null,
       count(*) FILTER (WHERE val = '0') AS n_zero,
       count(*) FILTER (WHERE val NOT IN ('null', '0')) AS n_pos
FROM raw_messages r, jsonb_each_text(r.extraction_result->'casualties') AS kv(key, val0),
     LATERAL (SELECT coalesce(val0, 'null') AS val) z
WHERE r.extraction_result IS NOT NULL AND (r.extraction_result->>'is_relevant')::boolean
  AND key IN ('deaths', 'injuries', 'total_deaths', 'total_injuries')
GROUP BY key ORDER BY key
"""

BULLETIN_SQL = """
SELECT breakdown_status::text, count(*), count(*) FILTER (WHERE total_deaths IS NOT NULL OR total_injuries IS NOT NULL) AS with_total
FROM bulletin_casualty_groups GROUP BY 1
"""


def pct(n: int, d: int) -> str:
    return f"{(100.0 * n / d):.1f}%" if d else "n/a"


def snippet(text: str, patterns: list[str], width: int = 110) -> str:
    """Trim raw text to the sentence around the first casualty/revision cue."""
    src = (text or "").replace("\n", " ")
    # Keep offsets aligned with src: only 1:1 substitutions here.
    norm = re.sub("[ً-ٰٟـ]", "_", src.translate(str.maketrans("أإآٱ", "اااا")))
    norm = re.sub(r"الشهيد(\s*)علي(\s*)شعيب", lambda mm: "#" * len(mm.group(0)), norm)
    for pat in patterns:
        m = re.search(pat.replace("[:alpha:]", "\\w"), norm)
        if m:
            start = max(0, m.start() - width)
            end = min(len(src), m.end() + width)
            return ("…" if start else "") + src[start:end].strip() + ("…" if end < len(src) else "")
    return src[: 2 * width] + ("…" if len(src) > 2 * width else "")


def main() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(url)
    conn.set_session(readonly=True, autocommit=False)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SET TRANSACTION READ ONLY")
    cur.execute("SHOW transaction_read_only")
    print("transaction_read_only =", cur.fetchone()["transaction_read_only"])

    params = dict(
        kw_strict=KW_STRICT, kw_weak=KW_WEAK, weak_fp=WEAK_FP, zero=ZERO, num_text=NUM_TEXT,
        wordnum=WORDNUM, revision=REVISION, cumulative=CUMULATIVE,
    )
    cur.execute(BASE_CTE, params)
    msgs = cur.fetchall()
    cur.execute(INCIDENTS_SQL)
    incidents = cur.fetchall()
    cur.execute(MERGE_FILL_SQL)
    merge_updates = cur.fetchall()

    inc_by_msg: dict[int, list[dict]] = defaultdict(list)
    for inc in incidents:
        if inc["raw_message_id"] is not None:
            inc_by_msg[inc["raw_message_id"]].append(inc)
    merges_by_inc: dict[str, list[dict]] = defaultdict(list)
    for u in merge_updates:
        merges_by_inc[u["incident_id"]].append(u)

    mat = [m for m in msgs if m["n_inc"] > 0]
    dates = [m["event_date"] for m in mat if m["event_date"]]
    print(f"\n=== UNIVERSE ===")
    print(f"relevant extracted messages: {len(msgs)}; with >=1 live incident: {len(mat)}; "
          f"live incidents: {len(incidents)}; event_date window {min(dates)}..{max(dates)}")

    # ---------------- bucket counts
    order = ["A", "B", "C", "D", "X", "F0", "F"]
    for label, universe in (("MATERIALIZED messages (primary)", mat), ("ALL relevant extracted messages", msgs)):
        c = Counter(m["bucket"] for m in universe)
        e = sum(1 for m in universe if m["revision"])
        print(f"\n=== BUCKETS: {label} (n={len(universe)}) ===")
        for b in order:
            n_inc = sum(len(inc_by_msg.get(m["id"], [])) for m in universe if m["bucket"] == b)
            print(f"{b:>3}: {c[b]:5d} msgs ({pct(c[b], len(universe))})  incidents={n_inc}")
        print(f"  E (revision language overlay): {e} ({pct(e, len(universe))})")
        ec = Counter(m["bucket"] for m in universe if m["revision"])
        print(f"  E by primary bucket: {dict(ec)}")
        cum = sum(1 for m in universe if m["cumulative"])
        print(f"  cumulative-toll language (MoH totals etc.): {cum}")
        by_status = Counter((m["status"], m["bucket"]) for m in universe)
        if label.startswith("ALL"):
            print("  status x bucket:", dict(sorted(by_status.items())))

    # ---------------- detail per bucket (materialized)
    def inc_summary(m: dict) -> str:
        rows = inc_by_msg.get(m["id"], [])
        return "; ".join(
            f"{r['id'][:8]} {r['village']}: d={r['deaths']} i={r['injuries']} td={r['total_deaths']} ti={r['total_injuries']}"
            f" [{r['verification_status']}{' dup' if r['duplicate_flag'] else ''}]"
            for r in rows
        )

    pats = {
        "A": [NUM_TEXT, KW_STRICT], "B": [NUM_TEXT, KW_STRICT], "C": [KW_STRICT, KW_WEAK],
        "D": ["(ال)?حصيلة", NUM_TEXT, KW_STRICT], "X": [NUM_TEXT], "E": [REVISION],
    }
    for b in ["A", "B", "C", "D", "X", "E"]:
        pool = [m for m in mat if (m["revision"] if b == "E" else m["bucket"] == b)]
        pool.sort(key=lambda m: m["id"], reverse=True)
        step = max(1, len(pool) // max(1, EXAMPLES))
        chosen = pool[::step][:EXAMPLES]
        print(f"\n=== EXAMPLES bucket {b} ({len(pool)} msgs) ===")
        for m in chosen:
            print(f"- msg {m['id']} [{m['status']}] scope={m['casualty_scope']} scope_review={m['scope_needs_review']} "
                  f"n_loc={m['n_loc']} n_loc_num={m['n_loc_num']} root(td,ti,d,i)=({m['root_td']},{m['root_ti']},{m['root_d']},{m['root_i']})"
                  f" rev={m['revision']} cum={m['cumulative']}")
            print(f"    text: {snippet(m['raw_text'], pats[b])}")
            if m["scope_evidence"]:
                print(f"    scope_evidence: {m['scope_evidence'][:200]}")
            print(f"    incidents: {inc_summary(m)}")

    # ---------------- gap analysis
    print("\n=== GAP: needs_verification on C / D / E / X incidents ===")
    for b in ["C", "D", "X", "E", "A", "B"]:
        rows = [
            r for m in mat if (m["revision"] if b == "E" else m["bucket"] == b)
            for r in inc_by_msg.get(m["id"], [])
        ]
        nv = [r for r in rows if r["verification_status"] == "needs_verification"]
        visible = [r for r in nv if r["duplicate_flag"]]
        reasons = Counter((r["verification_reason"] or "(null)")[:70] for r in nv)
        print(f"{b}: incidents={len(rows)} stored_NV={len(nv)} ({pct(len(nv), len(rows))}) "
              f"visible_NV={len(visible)} not_flagged={len(rows) - len(nv)}")
        for reason, n in reasons.most_common(6):
            print(f"     {n:4d}  {reason}")

    # ---------------- C: did a later message / merge supply a number?
    print("\n=== C: later number supplied? ===")
    by_village: dict[int, list[dict]] = defaultdict(list)
    by_story: dict[str, list[dict]] = defaultdict(list)
    for r in incidents:
        if r["village_id"] is not None:
            by_village[r["village_id"]].append(r)
        if r["story_group_id"]:
            by_story[r["story_group_id"]].append(r)

    def has_numbers(r: dict) -> bool:
        return any(r[k] is not None for k in ("deaths", "injuries", "total_deaths", "total_injuries"))

    c_rows = [r for m in mat if m["bucket"] == "C" for r in inc_by_msg.get(m["id"], [])]
    filled_now = [r for r in c_rows if has_numbers(r)]
    filled_by_merge = [
        r for r in filled_now
        if any(
            any(u["new_values"].get(k) is not None for k in ("deaths", "injuries", "total_deaths", "total_injuries"))
            for u in merges_by_inc.get(r["id"], [])
        )
    ]
    sibling = []
    for r in c_rows:
        if has_numbers(r):
            continue
        cands = {s["id"]: s for s in by_village.get(r["village_id"], [])}
        if r["story_group_id"]:
            cands.update({s["id"]: s for s in by_story.get(r["story_group_id"], [])})
        for s in cands.values():
            if (
                s["id"] != r["id"] and s["raw_message_id"] != r["raw_message_id"] and has_numbers(s)
                and s["created_at"] >= r["created_at"]
                and abs((s["event_date"] - r["event_date"]).days) <= 1
                and (s["deaths"] or s["injuries"] or s["total_deaths"] or s["total_injuries"])
            ):
                sibling.append((r, s))
                break
    print(f"C incidents: {len(c_rows)}; now carry a number: {len(filled_now)} "
          f"(of which merge-log shows a pipeline_merge write of a count: {len(filled_by_merge)})")
    print(f"C incidents still null but a LATER separate incident (same village or story group, ±1 day) has >0 counts: {len(sibling)}")
    for r, s in sibling[:6]:
        print(f"   C {r['id'][:8]} msg {r['raw_message_id']} {r['village']} {r['event_date']} -> later {s['id'][:8]} msg {s['raw_message_id']} "
              f"d={s['deaths']} i={s['injuries']} td={s['total_deaths']} ti={s['total_injuries']} [{s['verification_status']}]")
    nv_c_filled = [r for r in filled_now if r["verification_status"] == "needs_verification"]
    print(f"C incidents that now carry a number but are still stored NV: {len(nv_c_filled)}")
    dup_c = [m for m in msgs if m["bucket"] == "C" and m["status"] == "duplicate"]
    canon_num = sum(
        1 for m in dup_c
        if m["duplicate_of_id"] and any(has_numbers(r) for r in inc_by_msg.get(m["duplicate_of_id"], []))
    )
    canon_any = sum(1 for m in dup_c if m["duplicate_of_id"] and inc_by_msg.get(m["duplicate_of_id"]))
    print(f"C messages with status=duplicate (not in primary universe): {len(dup_c)}; "
          f"canonical message has live incidents: {canon_any}; canonical incident carries a number: {canon_num}")

    # C sub-types (first matching rule wins)
    print("\n=== C sub-types (why no number) ===")
    for label, universe in (("materialized", [m for m in mat if m["bucket"] == "C"]),
                            ("all relevant", [m for m in msgs if m["bucket"] == "C"])):
        sub = Counter()
        sub_examples: dict[str, list[dict]] = defaultdict(list)
        for m in universe:
            key = next((name for name, pat in C_SUBTYPES if re.search(pat, m["t"])), "C5 other / weak-only")
            sub[key] += 1
            sub_examples[key].append(m)
        print(f"{label}: n={len(universe)}")
        for name, _ in list(C_SUBTYPES) + [("C5 other / weak-only", "")]:
            print(f"   {sub[name]:4d} ({pct(sub[name], len(universe))})  {name}")
        if label == "materialized":
            for name, rows in sub_examples.items():
                for m in rows[:3]:
                    pat = dict(C_SUBTYPES).get(name, KW_WEAK)
                    print(f"      [{name[:2]}] msg {m['id']}: {snippet(m['raw_text'], [pat], 70)}")

    # ---------------- D: Bug A leak
    print("\n=== D / multi-village: aggregate stamped on individual rows (Bug A leak) ===")
    leak = []
    for m in mat:
        rows = inc_by_msg.get(m["id"], [])
        if len({r["village_id"] for r in rows}) < 2:
            continue
        for col_row, col_root in (("deaths", "root_d"), ("total_deaths", "root_td"),
                                  ("injuries", "root_i"), ("total_injuries", "root_ti")):
            vals = [r[col_row] for r in rows if r[col_row]]
            same = Counter(vals)
            for v, n in same.items():
                if n >= 2 and v > 0:
                    agg = m[col_root] if m[col_root] is not None else m["root_td"] if "death" in col_row else m["root_ti"]
                    leak.append((m, col_row, v, n, agg))
    leak_msgs = {m["id"] for m, *_ in leak}
    print(f"multi-village messages with the SAME non-zero count on >=2 village rows: {len(leak_msgs)}")
    print(f"  of which bucket D: {sum(1 for m, *_ in leak if m['bucket'] == 'D')} rows-hits, "
          f"distinct D msgs {len({m['id'] for m, *_ in leak if m['bucket'] == 'D'})}")
    seen = set()
    for m, col, v, n, agg in leak:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        print(f"- msg {m['id']} bucket={m['bucket']} {col}={v} on {n} rows (root aggregate={agg}) scope={m['casualty_scope']}")
        print(f"    text: {snippet(m['raw_text'], ['(ال)?حصيلة', NUM_TEXT])}")
        print(f"    incidents: {inc_summary(m)}")
        merged_ids = [r["id"][:8] for r in inc_by_msg.get(m["id"], []) if merges_by_inc.get(r["id"])]
        print(f"    rows with pipeline_merge history: {merged_ids}")
        if len(seen) >= 8:
            break
    d_msgs = [m for m in mat if m["bucket"] == "D"]
    d_null_rows = sum(1 for m in d_msgs for r in inc_by_msg.get(m["id"], []) if not has_numbers(r))
    d_rows = sum(len(inc_by_msg.get(m["id"], [])) for m in d_msgs)
    print(f"D rows with all-null counts (aggregate correctly NOT stamped): {d_null_rows}/{d_rows}")
    print(f"D msgs with casualty_scope=bulletin_aggregate: {sum(1 for m in d_msgs if m['casualty_scope'] == 'bulletin_aggregate')}; "
          f"scope field absent: {sum(1 for m in d_msgs if m['casualty_scope'] is None)}; "
          f"unspecified: {sum(1 for m in d_msgs if m['casualty_scope'] == 'unspecified')}; "
          f"per_village_exact: {sum(1 for m in d_msgs if m['casualty_scope'] == 'per_village_exact')}")
    print(f"D msgs where extraction kept NO number (aggregate only in text): {sum(1 for m in d_msgs if not m['has_num'])}")
    cur.execute(BULLETIN_SQL)
    print("bulletin_casualty_groups:", cur.fetchall())

    # ---------------- NULL vs 0
    print("\n=== NULL vs 0 (live incidents) ===")
    cur.execute(NULL_ZERO_SQL)
    for row in cur.fetchall():
        print(dict(row))
    cur.execute(COMBO_SQL)
    print("deaths/total_deaths null/zero combos:", [tuple(r.values()) for r in cur.fetchall()])
    cur.execute(ROOT_ZERO_SQL)
    print("extraction root casualties (relevant msgs):", [dict(r) for r in cur.fetchall()])
    zero_rows = [(m, r) for m in mat for r in inc_by_msg.get(m["id"], [])
                 if 0 in (r["deaths"], r["injuries"], r["total_deaths"], r["total_injuries"])]
    print(f"incident rows with any 0 count: {len(zero_rows)}; text has explicit-zero statement: "
          f"{sum(1 for m, _ in zero_rows if m['zero_stmt'])}; text has casualty keyword: {sum(1 for m, _ in zero_rows if m['cas_kw'])}")
    for m, r in zero_rows[:6]:
        print(f"   msg {m['id']} bucket={m['bucket']} zero_stmt={m['zero_stmt']} d={r['deaths']} i={r['injuries']} td={r['total_deaths']} ti={r['total_injuries']}")
        print(f"      {snippet(m['raw_text'], [ZERO, KW_STRICT, KW_WEAK], 80)}")
    f0 = [m for m in mat if m["bucket"] == "F0"]
    f0_rows = [r for m in f0 for r in inc_by_msg.get(m["id"], [])]
    print(f"F0 (explicit 'no casualties' text) msgs={len(f0)} rows={len(f0_rows)}: rows stored 0 = "
          f"{sum(1 for r in f0_rows if 0 in (r['deaths'], r['injuries'], r['total_deaths'], r['total_injuries']))}, "
          f"rows all-null = {sum(1 for r in f0_rows if not has_numbers(r))}")

    # ---------------- Arabic singular / dual without digits
    print("\n=== Arabic singular/dual forms without an adjacent digit ===")
    forms = {
        "dual_death (شهيدان/شهيدين/شهيدتان/شهيدتين/قتيلان/قتيلين) -> expect 2": (
            r"(?<![\w])(?:و|ف|ب)?(شهيدان|شهيدين|شهيدتان|شهيدتين|قتيلان|قتيلين)(?![\w])", "d", 2),
        "dual_injury (جريحان/جريحين/جريحتان/جريحتين/مصابان) -> expect 2": (
            r"(?<![\w])(?:و|ف|ب)?(جريحان|جريحين|جريحتان|جريحتين|مصابان)(?![\w])", "i", 2),
        "single_death (شهيد/شهيدا/شهيدة/قتيل, no ال) -> expect >=1": (
            r"(?<![\w])(?:و|ف|ب)?(شهيد|شهيدا|شهيدة|قتيل|قتيلا|قتيلة)(?![\w])", "d", 1),
        "single_injury (جريح/جريحا/جريحة, no ال) -> expect >=1": (
            r"(?<![\w])(?:و|ف|ب)?(جريح|جريحا|جريحة)(?![\w])", "i", 1),
    }
    for label, (pat, kind, expect) in forms.items():
        hits = []
        for m in msgs:
            for mm in re.finditer(pat, m["t"]):
                before = m["t"][max(0, mm.start() - 6):mm.start()]
                if re.search(r"[0-9٠-٩]", before):
                    continue
                hits.append(m)
                break
        outcome = Counter()
        bad = []
        for m in hits:
            if kind == "d":
                vals = [m["root_td"], m["root_d"]] + [r["deaths"] for r in inc_by_msg.get(m["id"], [])] + [r["total_deaths"] for r in inc_by_msg.get(m["id"], [])]
            else:
                vals = [m["root_ti"], m["root_i"]] + [r["injuries"] for r in inc_by_msg.get(m["id"], [])] + [r["total_injuries"] for r in inc_by_msg.get(m["id"], [])]
            vals = [v for v in vals if v is not None]
            if not vals:
                key = "null (missed)"
            elif expect == 2 and 2 in vals:
                key = "2 (correct)"
            elif expect == 1 and any(v >= 1 for v in vals):
                key = ">=1 (plausible)"
            else:
                key = f"other {sorted(set(vals))}"
            outcome[key] += 1
            if key.startswith(("null", "other")):
                bad.append(m)
        print(f"{label}: msgs={len(hits)} outcome={dict(outcome)}")
        for m in bad[:3]:
            print(f"    miss msg {m['id']} [{m['status']}] bucket={m['bucket']}: {snippet(m['raw_text'], [pat.replace('(?<![\\w])', '').replace('(?![\\w])', '')], 70)}")
    wn = [m for m in msgs if m["wordnum_text"]]
    wn_num = sum(1 for m in wn if m["has_num"])
    print(f"spelled-out numbers >=2 (ثلاثة شهداء ...): msgs={len(wn)}, extraction kept a number: {wn_num}, null: {len(wn) - wn_num}")
    for m in [m for m in wn if not m["has_num"]][:4]:
        print(f"    msg {m['id']} [{m['status']}] bucket={m['bucket']}: {snippet(m['raw_text'], [WORDNUM], 70)}")

    # ---------------- flag volume
    print("\n=== FLAG VOLUME (per incident event_date, materialized) ===")
    per_day_msgs: dict = defaultdict(lambda: Counter())
    for m in mat:
        d = m["event_date"]
        key_c = m["bucket"] == "C"
        key_d = m["bucket"] == "D"
        key_e = bool(m["revision"])
        per_day_msgs[d]["all"] += 1
        per_day_msgs[d]["inc_all"] += len(inc_by_msg.get(m["id"], []))
        if key_c or key_d or key_e:
            per_day_msgs[d]["CDE_msgs"] += 1
            per_day_msgs[d]["CDE_inc"] += len(inc_by_msg.get(m["id"], []))
        for k, flag in (("C", key_c), ("D", key_d), ("E", key_e)):
            if flag:
                per_day_msgs[d][k] += 1
    days = sorted(per_day_msgs)
    print(f"days with >=1 materialized message: {len(days)} ({days[0]}..{days[-1]})")
    for k in ("all", "inc_all", "C", "D", "E", "CDE_msgs", "CDE_inc"):
        series = [per_day_msgs[d][k] for d in days]
        s_sorted = sorted(series)
        p90 = s_sorted[int(0.9 * (len(s_sorted) - 1))]
        print(f"{k:>9}: mean={statistics.mean(series):.1f} median={statistics.median(series)} p90={p90} max={max(series)} total={sum(series)}")
    print("per-day detail (date: msgs / C / D / E / CDE msgs / CDE incidents):")
    for d in days:
        c = per_day_msgs[d]
        print(f"   {d}: {c['all']:3d} / {c['C']:2d} / {c['D']:2d} / {c['E']:2d} / {c['CDE_msgs']:3d} / {c['CDE_inc']:3d}")

    conn.rollback()
    conn.close()
    print("\nrolled back; read-only session closed")


if __name__ == "__main__":
    main()
