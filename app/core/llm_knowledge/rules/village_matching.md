# Village matching rules

## Fuzzy match thresholds

- `MATCH_THRESHOLD = 0.6` for confident match.
- `LOW_CONFIDENCE_THRESHOLD = 0.35` for review-tier match.
- `MATCH_TIE_MARGIN = 0.05` - if top two scores differ by less than this at >=0.6, demote to `matched_low_confidence`.

## Collision detection

When >=2 candidates share the same `ref_name_ar` prefix as the mention (e.g. five *النبطية* villages at ~0.615), treat as collision-like and demote confidence.

## Location aliases

Evidence-backed aliases in `village_location_aliases` resolve exact normalized mentions to a parent village ACS row (e.g. «النبطية» -> Nabatieh Et-Tahta 71111, «حي المسلخ» -> same).

Do not fuzzy-match bare ambiguous tokens without alias when multiple ACS rows tie.

Specific collision guard: «وادي السلوقي», «السلوقي», and spelling/Latin variants in recurring south-Lebanon Wadi el-Selouqi bulletins resolve to Touline / تولين (ACS 73282). Do not allow trigram similarity to resolve those mentions to Slouqi/Slouky Baalbek (ACS 53423).

## Geo-context disambiguation

When fuzzy scores tie and candidates have coordinates:
- Prefer candidate nearest to an already-resolved anchor village in the same bulletin.
- Requires minimum distance advantage over original top candidate.

## Condition disambiguation tokens

Some condition IDs require distinguishing substrings in the action text:
- ID 2 (warning raid): requires «تحذيريه»
- ID 39 (feigned attack): requires «وهميه»

## Dash-route extraction (upstream)

Before matching, Tier 1 should split `طريق ... X - Y` into two village mentions for separate match attempts.
