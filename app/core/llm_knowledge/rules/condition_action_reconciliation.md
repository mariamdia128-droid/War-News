# Condition/action reconciliation

When extracting conflict incidents, preserve the most specific action phrase
grounded in the bulletin text. The action text and evidence span drive the
primary condition candidate.

Source-provided event metadata, such as CNRS `event_subtype`, is a secondary
hint. It must not overwrite a specific text-grounded action such as `تمشيط`,
`قنابل مضيئة`, tank fire, warning raid, or feigned raid.

Generic attack wording `قصف`, `غارة`, `غارات`, `غارة جوية`, `غارات جوية`,
`استهداف`, and `استهدف` maps to plain `Bombs`. A more specific phrase always
wins, including `قصف مدفعي` → `Artillery Shelling` and `قنابل مضيئة` →
`Flare Bomb`.

Bare `مسيرة` / `مسيّرة` / `طيران مسير` is a drone reference, not evidence of
`Drone Failure` or `Suicide Drone`. Those conditions require explicit crash or
explosive wording. A drone phrase with strike wording (`استهدفت`, `غارة`, or
`صاروخ`) is a strike and maps to `Bombs`; otherwise leave it to air-activity
handling.

If the bulletin contains multiple village-local actions, emit scoped
`sub_events` so each village is matched against its own action. Use root
`action_description` only as a fallback summary when the message has one
condition.

If the action cannot be identified from the bulletin text, leave the extracted
action empty rather than rounding to a generic bucket. The matching layer may
use source metadata as a review-required fallback.

## Flare Bomb vs Bombs

Classify illumination/flare munitions as the specific action `Flare Bomb`, not
plain `Bombs`, when the text says `قنابل مضيئة`, `قنبلة مضيئة`,
`قنابل إنارة`, `قنبلة إنارة`, `قنابل ضوئية`, `بالونات حرارية`,
`flares`, or `illumination flares`. These light the ground and do not by
themselves describe a strike, explosion, damage, fire, or casualties.

Do not classify as plain `Bombs` just because the word `قنابل` appears.
Plain `Bombs` requires an actual strike, shelling, targeting, explosion, or
impact: `غارة`, `غارات`, `قصف`, `استهداف`, `استهدف`, `انفجار`.
Likewise, sound bombs, smoke bombs, and tear-gas bombs are not plain `Bombs`
unless the text also describes an actual strike/impact.

Incendiary (`حارقة`) and phosphorus (`فوسفورية`) munitions that hit a target,
start fires, cause damage, or cause casualties are not plain illumination
flares. Keep them as the appropriate strike/munition action, and flag for
review when the wording is unclear.

If one message describes both a real strike and flare bombs, emit separate
`sub_events` with their own `action_text` and `evidence_span`; do not merge
the flare action into the strike. If flares are only background context before
or after a strike, do not create a separate `Flare Bomb` action.

Examples:
- `الطائرات الإسرائيلية تلقي قنابل مضيئة على بلدة المنصوري في قضاء صور`
  -> `action_description="Flare Bomb"`
- `الاحتلال يلقي قنابل مضيئة في محيط حداثا`
  -> `action_description="Flare Bomb"`
- `الطيران الحربي يلقي قنابل على أطراف بلدة عيتا الشعب`
  -> `action_description="Bombs"`
- `غارة إسرائيلية استهدفت منزلا في بلدة المنصوري`
  -> `action_description="Bombs"`
