# llm_knowledge live validation run

**Date (UTC):** 2026-09-14T08:45:45.584333+00:00
**Model:** `qwen2.5:7b`
**Summary:** 11 pass / 1 partial / 4 fail

Policy: `expected_output` was **not** edited to match the model. Mismatches are left for manual review.

| # | bug_ref | corpus | verdict | note | seconds |
|---|---------|--------|---------|------|--------:|
| 1 | `multi-village-casualty-misattribution` | `casualty_scope.jsonl` | **pass** | casualty_scope=bulletin_aggregate:Y | 140.3 |
| 2 | `multi-village-null-not-zero-or-shared` | `casualty_scope.jsonl` | **fail** | casualty_scope=per_village_exact:N | 259.1 |
| 3 | `merge-blind-max-wins` | `casualty_scope.jsonl` | **pass** | casualty_transitions:Y | 8.1 |
| 4 | `preliminary-toll-revision` | `revision_detection.jsonl` | **fail** | expected revision, got None | 1.5 |
| 5 | `named-victim-zahraa-revision` | `revision_detection.jsonl` | **fail** | expected revision, got None | 4.7 |
| 6 | `rising-toll-revision` | `revision_detection.jsonl` | **pass** | revision + marker | 1.5 |
| 7 | `preliminary-tally-marker` | `revision_detection.jsonl` | **fail** | expected revision, got None | 8.0 |
| 8 | `vague-quantifier-null` | `tier1_extraction.jsonl` | **pass** | casualties.deaths=null:Y, casualties.injuries=null:Y | 9.1 |
| 9 | `gendered-occupation-paramedic-in-mixed-toll` | `tier1_extraction.jsonl` | **partial** | casualties.deaths=8:Y, casualties.injuries=11:Y, casualties.male_deaths>=1:N | 10.7 |
| 10 | `casualty-transition-followup` | `tier1_extraction.jsonl` | **pass** | casualty_transitions:Y | 6.5 |
| 11 | `transition-with-restated-remaining-injuries` | `tier1_extraction.jsonl` | **pass** | casualty_transitions:Y | 9.4 |
| 12 | `additive-injuries-not-transition` | `tier1_extraction.jsonl` | **pass** | casualty_transitions=[]:Y | 8.4 |
| 13 | `occupation-gender-male-paramedic` | `tier1_extraction.jsonl` | **pass** | casualties.male_deaths=1:Y | 24.4 |
| 14 | `occupation-gender-female-paramedic` | `tier1_extraction.jsonl` | **pass** | casualties.female_deaths=1:Y | 5.1 |
| 15 | `maslakh-neighborhood` | `village_matching.jsonl` | **pass** | ACS 71111 | 9.1 |
| 16 | `bare-fouqa-collision` | `village_matching.jsonl` | **pass** | left unresolved/ambiguous | 1.3 |

## Per-case detail

### 1. `multi-village-casualty-misattribution` — pass

- corpus: `casualty_scope.jsonl` / stage `casualty_scope` (prompt `combined_tier1`)
- note: casualty_scope=bulletin_aggregate:Y

Input:

```
المنصوري ومجدل زون: 5 شهداء و12 جريحاً
```

Expected:

```json
{
  "casualty_scope": "bulletin_aggregate",
  "note": "shared colon tally must not be copied as per-village 5/12 to each village"
}
```

_Actual omitted (pass)._

### 2. `multi-village-null-not-zero-or-shared` — fail

- corpus: `casualty_scope.jsonl` / stage `casualty_scope` (prompt `combined_tier1`)
- note: casualty_scope=per_village_exact:N

Input:

```
قصف على المنصوري أدى إلى شهيد و3 جرحى، وفي مجدل زون سقطت قذيفة دون إصابات
```

Expected:

```json
{
  "casualty_scope": "per_village_exact",
  "village_roles": [
    {
      "village": "المنصوري",
      "deaths": 1,
      "injuries": 3
    },
    {
      "village": "مجدل زون",
      "deaths": null,
      "injuries": null
    }
  ]
}
```

Actual (failure/partial):

```json
{
  "categories_present": [
    "casualty_demographics"
  ],
  "category_evidence": [
    {
      "category_key": "casualty_demographics",
      "evidence_span": "شهدى و3 جرحى"
    }
  ],
  "is_relevant": true,
  "village": [
    "المنصوري",
    "مجدل زون"
  ],
  "village_roles": [
    {
      "village": "المنصوري",
      "role": "target",
      "deaths": 1,
      "injuries": 3,
      "evidence_span": "قصف على المنصوري أدى إلى شهيد و3 جرحى"
    },
    {
      "village": "مجدل زون",
      "role": "target",
      "deaths": 0,
      "injuries": 0,
      "evidence_span": "وفي مجدل زون سقطت قذيفة دون إصابات"
    }
  ],
  "action_description": "قصف",
  "sub_events": [
    {
      "deaths": 1,
      "injuries": 3,
      "evidence_span": "قصف على المنصوري أدى إلى شهيد و3 جرحى"
    },
    {
      "deaths": 0,
      "injuries": 0,
      "evidence_span": "وفي مجدل زون سقطت قذيفة دون إصابات"
    }
  ],
  "casualties": {
    "total_deaths": 1,
    "total_injuries": 3,
    "deaths": 1,
    "injuries": 3,
    "male_deaths": 1,
    "male_injuries": 3,
    "female_deaths": null,
    "female_injuries": null,
    "children_deaths": null,
    "children_injuries": null
  },
  "casualty_evidence": [
    {
      "field": "deaths",
      "evidence_span": "شهدى"
    },
    {
      "field": "injuries",
      "evidence_span": "3 جرحى"
    }
  ],
  "casualty_scope": "bulletin_aggregate",
  "casualty_scope_evidence": "وفي مجدل زون سقطت قذيفة دون إصابات",
  "casualty_transitions": []
}
```

**Reviewer note:** treat as prompt/knowledge gap unless expected_output is demonstrably wrong; do not auto-edit the corpus.

### 3. `merge-blind-max-wins` — pass

- corpus: `casualty_scope.jsonl` / stage `casualty_scope` (prompt `combined_tier1`)
- note: casualty_transitions:Y

Input:

```
بقي 3 جرحى وتوفي واحد من جرحى الغارة السابقة على عيتا الشعب
```

Expected:

```json
{
  "casualty_transitions": [
    {
      "from_status": "injured",
      "to_status": "deceased",
      "count": 1
    }
  ],
  "merge_rule": "apply_transition_before_max_wins",
  "note": "transition must win over restated injuries=3; do not blindly max(old,new)"
}
```

_Actual omitted (pass)._

### 4. `preliminary-toll-revision` — fail

- corpus: `revision_detection.jsonl` / stage `story_revision` (prompt `story_revision`)
- note: expected revision, got None

Input:

```
غارة من الطيران المسير استهدفت سيارة في بلدة كفررمان والمعلومات الأولية تشير إلى وقوع إصابتين
```

Expected:

```json
{
  "relationship_hint": "revision",
  "matched_keyword_contains": "المعلومات الأولية"
}
```

Actual (failure/partial):

```json
{
  "relationship_hint": null,
  "matched_keywords": []
}
```

**Reviewer note:** treat as prompt/knowledge gap unless expected_output is demonstrably wrong; do not auto-edit the corpus.

### 5. `named-victim-zahraa-revision` — fail

- corpus: `revision_detection.jsonl` / stage `story_revision` (prompt `story_revision`)
- note: expected revision, got None

Input:

```
بلدية كفررمان تنعى الموظفة في البلدية زهراء أيوب، التي ارتقت شهيدة مع أفراد عائلتها إثر الغارة الإسرائيلية التي استهدفت منزلهم ليلاً في البلدة
```

Expected:

```json
{
  "relationship_hint": "revision",
  "matched_keyword_contains": "تنعى",
  "requires_numeric_candidate": true
}
```

Actual (failure/partial):

```json
{
  "relationship_hint": null,
  "matched_keywords": []
}
```

**Reviewer note:** treat as prompt/knowledge gap unless expected_output is demonstrably wrong; do not auto-edit the corpus.

### 6. `rising-toll-revision` — pass

- corpus: `revision_detection.jsonl` / stage `story_revision` (prompt `story_revision`)
- note: revision + marker

Input:

```
ارتفاع عدد الجرحى في غارة كفررمان إلى 11
```

Expected:

```json
{
  "relationship_hint": "revision",
  "matched_keyword_contains": "ارتفاع عدد"
}
```

_Actual omitted (pass)._

### 7. `preliminary-tally-marker` — fail

- corpus: `revision_detection.jsonl` / stage `story_revision` (prompt `story_revision`)
- note: expected revision, got None

Input:

```
حصيلة أولية للغارة على ياطر: شهيدان و4 جرحى
```

Expected:

```json
{
  "relationship_hint": "revision",
  "matched_keyword_contains": "حصيلة أولية"
}
```

Actual (failure/partial):

```json
{
  "relationship_hint": null,
  "matched_keywords": []
}
```

**Reviewer note:** treat as prompt/knowledge gap unless expected_output is demonstrably wrong; do not auto-edit the corpus.

### 8. `vague-quantifier-null` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualties.deaths=null:Y, casualties.injuries=null:Y

Input:

```
عشرات الجرحى والشهداء
```

Expected:

```json
{
  "casualties": {
    "deaths": null,
    "injuries": null
  }
}
```

_Actual omitted (pass)._

### 9. `gendered-occupation-paramedic-in-mixed-toll` — partial

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualties.deaths=8:Y, casualties.injuries=11:Y, casualties.male_deaths>=1:N

Input:

```
غارة العدو الإسرائيلي على منزل في بلدة كفررمان أدت إلى 8 شهداء من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان واستشهاد مسعف
```

Expected:

```json
{
  "casualties": {
    "deaths": 8,
    "injuries": 11,
    "male_deaths_at_least": 1
  },
  "note": "مسعف شهيد must contribute male_deaths without overwriting mixed toll"
}
```

Actual (failure/partial):

```json
{
  "categories_present": [
    "lebanese_army",
    "casualty_demographics",
    "hospital",
    "emergency_civil_defense"
  ],
  "category_evidence": [
    {
      "category_key": "lebanese_army",
      "evidence_span": "غارة العدو الإسرائيلي"
    },
    {
      "category_key": "casualty_demographics",
      "evidence_span": "8 شهداء من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان"
    },
    {
      "category_key": "hospital",
      "evidence_span": "استشهاد مسعف"
    },
    {
      "category_key": "emergency_civil_defense",
      "evidence_span": "استشهاد مسعف"
    }
  ],
  "is_relevant": true,
  "village": [
    "كفررمان"
  ],
  "village_roles": [
    {
      "village": "كفررمان",
      "role": "target",
      "deaths": 8,
      "injuries": 11,
      "evidence_span": "غارة العدو الإسرائيلي على منزل في بلدة كفررمان أدت إلى 8 شهداء من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان"
    }
  ],
  "action_description": "غارة",
  "sub_events": [
    {
      "deaths": 8,
      "injuries": 11,
      "male_deaths": null,
      "male_injuries": null,
      "female_deaths": 2,
      "female_injuries": 2,
      "children_deaths": 1,
      "children_injuries": 4,
      "evidence_span": "غارة العدو الإسرائيلي على منزل في بلدة كفررمان أدت إلى 8 شهداء من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان"
    }
  ],
  "casualties": {
    "total_deaths": 8,
    "total_injuries": 11,
    "deaths": 8,
    "injuries": 11,
    "male_deaths": null,
    "male_injuries": null,
    "female_deaths": 2,
    "female_injuries": 2,
    "children_deaths": 1,
    "children_injuries": 4
  },
  "casualty_evidence": [
    {
      "field": "deaths",
      "evidence_span": "8"
    },
    {
      "field": "injuries",
      "evidence_span": "11"
    },
    {
      "field": "female_deaths",
      "evidence_span": "سيدتان"
    },
    {
      "field": "female_injuries",
      "evidence_span": "سيدتان"
    },
    {
      "field": "children_deaths",
      "evidence_span": "طفل"
    },
    {
      "field": "children_injuries",
      "evidence_span": "4 أطفال"
    }
  ],
  "casualty_scope": "per_village_exact",
  "casualty_scope_evidence": "غارة العدو الإسرائيلي على منزل في بلدة كفررمان أدت إلى 8 شهداء من بينهم طفل وسيدتان و11 جريحا من بينهم 4 أطفال وسيدتان",
  "casualty_transitions": []
}
```

### 10. `casualty-transition-followup` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualty_transitions:Y

Input:

```
توفي أحد الجرحى جراء إصابته في الغارة على بلدة عيتا الشعب
```

Expected:

```json
{
  "casualty_transitions": [
    {
      "from_status": "injured",
      "to_status": "deceased",
      "count": 1
    }
  ]
}
```

_Actual omitted (pass)._

### 11. `transition-with-restated-remaining-injuries` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualty_transitions:Y

Input:

```
بقي 3 جرحى وتوفي واحد من جرحى الغارة
```

Expected:

```json
{
  "casualty_transitions": [
    {
      "from_status": "injured",
      "to_status": "deceased",
      "count": 1
    }
  ],
  "note": "do not treat remaining injuries as additive-only snapshot"
}
```

_Actual omitted (pass)._

### 12. `additive-injuries-not-transition` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualty_transitions=[]:Y

Input:

```
أصيب 5 جرحى جدد في قصف جديد على القرية
```

Expected:

```json
{
  "casualty_transitions": []
}
```

_Actual omitted (pass)._

### 13. `occupation-gender-male-paramedic` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualties.male_deaths=1:Y

Input:

```
شهيد مسعف في ياطر
```

Expected:

```json
{
  "casualties": {
    "male_deaths": 1
  }
}
```

_Actual omitted (pass)._

### 14. `occupation-gender-female-paramedic` — pass

- corpus: `tier1_extraction.jsonl` / stage `tier1_extraction` (prompt `combined_tier1`)
- note: casualties.female_deaths=1:Y

Input:

```
استشهاد مسعفة في بلدة عيتا الشعب
```

Expected:

```json
{
  "casualties": {
    "female_deaths": 1
  }
}
```

_Actual omitted (pass)._

### 15. `maslakh-neighborhood` — pass

- corpus: `village_matching.jsonl` / stage `village_matching` (prompt `village_matching`)
- note: ACS 71111

Input:

```
حي المسلخ
```

Expected:

```json
{
  "resolved_parent_acs": 71111,
  "note": "not Masqa المتن"
}
```

_Actual omitted (pass)._

### 16. `bare-fouqa-collision` — pass

- corpus: `village_matching.jsonl` / stage `village_matching` (prompt `village_matching`)
- note: left unresolved/ambiguous

Input:

```
الفوقا
```

Expected:

```json
{
  "match": null,
  "reason": "ambiguous_or_unresolved",
  "note": "bare الفوقا three-way tie"
}
```

_Actual omitted (pass)._


## Open review (mismatches not auto-resolved)

| bug_ref | Belief | Why |
|---------|--------|-----|
| `multi-village-null-not-zero-or-shared` | **prompt/knowledge gap** (primary) | Model correctly split village_roles (1/3 vs 0/0) but labeled `casualty_scope=bulletin_aggregate`. Expectation `per_village_exact` still looks correct; strengthen multi-village scope examples. Secondary: model used `0` instead of `null` for no-injury village. |
| `preliminary-toll-revision` | **prompt gap** | `story_revision` stage currently loads `casualty_merge.md`, not a revision-classifier prompt. Production uses keyword backstop (`المعلومات الأولية`). Corpus expectation matches backstop behavior; live LLM path is under-specified. |
| `named-victim-zahraa-revision` | **prompt gap** | Same as above; `تنعى` is backstop-first in production. |
| `preliminary-tally-marker` | **prompt gap** | Same; `حصيلة أولية` is in terminology but no dedicated revision system prompt. |
| `gendered-occupation-paramedic-in-mixed-toll` | **prompt/knowledge gap** | Totals 8/11 correct; `male_deaths` from `استشهاد مسعف` missing while `female_deaths` filled from سيدتان. Standalone occupation cases passed; mixed-toll gender still weak. Production gender backstop would often repair this after LLM. |

**Not done:** no `expected_output` edits; no silent corpus absorption of model answers.
