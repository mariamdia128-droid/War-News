# Story-continuation diagnosis: Kfar Roummane, 7 Sep 2026

This report is the Phase 5 investigation: why incidents #7 and #9 merged while the rest of the same-village cluster did not, and which candidate-search threshold that implies.

Live comparison used incident `khabar_embedding` (copied from `raw_messages.content_embedding`, 384-d `paraphrase-multilingual-MiniLM-L12-v2`) plus event times. Fast-path 30-minute same-condition matching was left unchanged.

## What succeeded (#7 / #9)

#7 (09:21, Bombs, house + car, ~11 martyrs / 5 injured) shows `Automatically merged — 92%`. The merge partners were later near-paraphrase copies of the same Ministry/NNA wording (embedding cosine **0.90–0.95**, `MatchType.exact` / `confirmed_duplicate`). Those copies arrived **~85 minutes** after 09:21.

That gap is **outside** the current 30-minute identity window (`dedup_fastpath_gap_mid_seconds=1800`). Today's fast path would treat a 85-minute paraphrase as `distinct`. The stored 92% badge is therefore from an earlier 6-hour embedding path (or event-time alignment), not from the current 30-minute gate. The 30-minute same-condition path is still the correct home for true near-duplicates and was not widened here.

#9 (02:34, Bombs, Kfar Roummane + Arbsalim) merged at 82% on the same-condition, high-text/embedding, short-window path — a genuine fast-path success.

## What failed, and why

Measured cosine similarities against the 11:33 full house+car report (#1):

| Pair | Gap | Conditions | Embedding | Why it did not merge |
|------|-----|------------|-----------|----------------------|
| #1 vs #8 (07:04 drone car) | ~4.5h | Bombs vs **Drone Failure** | **0.738** | Condition gate: never compared |
| #3 vs #8 (same car-strike) | ~4h | Bombs vs Drone Failure | **0.666** | Same gate |
| #1 vs #3 (11:00 MoH car) | **33 min** | both Bombs | **0.580** | 33 min > 30 min cutoff; text is car-only vs house+car |
| #1 vs Zahraa (11:31 named victim) | **2 min** | both Bombs | **0.586** | Same village+condition+window, but 0.586 << `dedup_fastpath_embedding_possible` 0.78 |
| #7 vs Zahraa | ~2h | both Bombs | **0.738** | Window + named-victim vs numeric framing |
| #1 vs #11 (02:21 sparse) | ~9h | both Bombs | **0.519** | Hours earlier; sparse "casualties occurred" |
| #1 vs #10 (02:22 preliminary car) | ~9h | both Bombs | **0.402** | Hours earlier; "المعلومات الأولية" / two injuries |
| #1 vs #7 | ~2h | both Bombs | **0.581** | Fast path never sees this pair today |

#8's live wording is the same car-strike as #3 (three paramedics, one martyred, two injured). Classifier rank prefers **duplicate of the car-only incident** over blending into #1's house+car totals.

## Is removing the condition gate enough?

No. Phase 1's 72-hour, no-condition candidate search is **necessary** (#8 vs Bombs) but **not sufficient**:

1. `story_candidate_embedding_threshold` started at **0.78** (`dedup_fastpath_embedding_possible`). That recovers #8 vs #1 (0.738) only if lowered; it still misses Zahraa (0.586) and the sparse precursors (0.40–0.52).
2. Fast-path 30-minute same-condition matching must stay tight. Widening *that* cutoff to catch #3 (33 min) or #10/#11 (hours) would reintroduce Mansouri-class false positives.
3. Precision for loosely worded early reports belongs in the Phase 2 classifier / `story_revision_backstop` (preliminary-toll and named-victim patterns), not in the 30-minute duplicate engine.

## Threshold adjustment

`story_candidate_embedding_threshold` is set to **0.40** so the 02:22 preliminary car report is retrievable against the later full report (measured 0.402). Classifier and backstop remain the precision filter.

The 0.78 fast-path embedding tier is unchanged. Story search also adds a **revision-keyword recall pass** (threshold 0.0, still same village + 72h, still capped at 10) when the incoming text has preliminary/named-victim markers, so a pair that sits just under 0.40 is not lost to embedding drift.

#8 (0.738) and Zahraa (0.586) are both above 0.40 without that fallback.
