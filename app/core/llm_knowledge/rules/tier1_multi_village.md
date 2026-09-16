# Tier 1 situational rules — multi-village bulletins

Load when the message appears to name multiple target locations.

## Detection signals

- Two or more place names in separate clauses (semicolon, colon, or list).
- Explicit route/path endpoints only: `طريق … X - Y`, `طريق عام X - Y`, or `بين X و Y` → two distinct villages/endpoints.
- Every other dash phrase defaults to one target on the left and qualifier context on the right: `بلدة X - حي Y`, `مزرعة X - Y`, `بلدة X - قضاء Y`, or `بلدة X - [neighborhood/hamlet]`.
- In `مزرعة X - Y وZ`, the complete `Y وZ` tail is qualifier context, not two additional targets.
- Multiple `target` entries in expected extraction.

## Extraction rules

1. Each target village gets its own `village_roles` entry.
2. Route endpoints (`طريق X - Y` or `بين X و Y`): emit both `X` and `Y` as separate target locations (and inside the same `sub_event.locations` if a single route action occurred).
3. For every non-route dash phrase, emit only the left side as the target and preserve the entire right side as `qualifier_text`, including any `و`-joined parts.
4. Copy per-village deaths/injuries only from that village's sentence or phrase.
5. If only a shared toll is given covering all villages → `casualty_scope: bulletin_aggregate`.
6. Put shared figures in `casualties.total_deaths` / `total_injuries`; leave `deaths`/`injuries` null.
7. `casualty_scope_evidence` must be the full clause showing whether the toll is shared or per-village.

## Examples

**Per-village exact:**
«المنصوري: شهيد و3 جرحى؛ مجدل زون: 4 جرحى»

**Bulletin aggregate:**
«غارة على المنصوري ومجدل زون أدت إلى 5 شهداء» (no per-village breakdown)

**Dash route / endpoints:**
«استهدف دراجة نارية على طريق عام مرج حاروف - زبدين» → village=["حاروف","زبدين"] (two target endpoints)
«غارة بين كفرتبنيت وزوطر الشرقية» → village=["كفرتبنيت","زوطر الشرقية"] (two target endpoints)

**Single target with qualifier / neighborhood:**
«غارة على بلدة كفررمان - حي الميدان» → village=["كفررمان"], village_roles=[{"village":"كفررمان","role":"target","qualifier_text":"حي الميدان"}]
«قصف على مزرعة حلتا - كفرشوبا» → village=["مزرعة حلتا"], village_roles=[{"village":"مزرعة حلتا","role":"target","qualifier_text":"كفرشوبا"}]
«غارة على مزرعة الحمرا - زوطر وتلة علي الطاهر» → village=["مزرعة الحمرا"], village_roles=[{"village":"مزرعة الحمرا","role":"target","qualifier_text":"زوطر وتلة علي الطاهر"}]
«غارة على بلدة المنصوري - حي غزاله» → village=["المنصوري"], qualifier_text="حي غزاله"
«غارة على بلدة كفررمان - النبطية» → village=["كفررمان"], qualifier_text="النبطية"
«غارة على بلدة الرمادية - قضاء صور» → village=["الرمادية"], qualifier_text="قضاء صور"
«غارة على بلدة المنصوري - بيوت السياد» → village=["المنصوري"], qualifier_text="بيوت السياد"

## Materialization note (downstream)

Multi-village bulletins suppress per-category casualty fields at Tier 2 until manually confirmed per village.
