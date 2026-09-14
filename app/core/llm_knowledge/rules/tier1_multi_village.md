# Tier 1 situational rules — multi-village bulletins

Load when the message appears to name multiple target locations.

## Detection signals

- Two or more place names in separate clauses (semicolon, colon, or list).
- Dash-joined route names: `طريق … X - Y` → two villages, not one compound.
- Multiple `target` entries in expected extraction.

## Extraction rules

1. Each target village gets its own `village_roles` entry.
2. Copy per-village deaths/injuries only from that village's sentence or phrase.
3. If only a shared toll is given covering all villages → `casualty_scope: bulletin_aggregate`.
4. Put shared figures in `casualties.total_deaths` / `total_injuries`; leave `deaths`/`injuries` null.
5. `casualty_scope_evidence` must be the full clause showing whether the toll is shared or per-village.

## Examples

**Per-village exact:**
«المنصوري: شهيد و3 جرحى؛ مجدل زون: 4 جرحى»

**Bulletin aggregate:**
«غارة على المنصوري ومجدل زون أدت إلى 5 شهداء» (no per-village breakdown)

**Dash route:**
«استهدف دراجة نارية على طريق عام مرج حاروف - زبدين» → village=["حاروف","زبدين"]

## Materialization note (downstream)

Multi-village bulletins suppress per-category casualty fields at Tier 2 until manually confirmed per village.
