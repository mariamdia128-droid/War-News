# Story revision detection

Classify whether the bulletin is a follow-up, correction, or update to an
earlier incident toll. Return `relationship_hint: "revision"` when any of the
following signals is present:

- Preliminary or provisional toll language: `حصيلة أولية`, `حصيلة مؤقتة`,
  `المعلومات الأولية`, or `معلومات أولية`.
- Toll updates or corrections: `تحديث الحصيلة`, `مراجعة الحصيلة`,
  `تصحيح الحصيلة`, `ارتفاع عدد`, or `ارتفع عدد` when it refers to deaths or
  injuries.
- A named-victim follow-up or obituary: `تنعى`/`تنعي`, a named employee or
  responder reported as having died, or a named martyr announcement that
  supplies detail about an earlier bulletin.

For a revision, include the literal matching marker(s) in
`matched_keywords`. A named-victim follow-up can be a revision even when the
new bulletin has no numeric toll, but it must describe a victim or death and
not merely mention a person's name.

Do not classify an ordinary first report as a revision. Do not infer a
revision only from a number, a casualty word, or a generic incident update
without one of the markers above.

Return exactly one JSON object with these keys:

```json
{"relationship_hint":"revision","matched_keywords":["حصيلة أولية"]}
```

For a non-revision bulletin, return:

```json
{"relationship_hint":null,"matched_keywords":[]}
```