# Review finding contract

Use this contract for every final review. Keep findings concise enough to act on without another investigation.

## Severity

- **P0 — Critical:** reliably causes catastrophic data loss, broad compromise, or total production failure; immediate intervention is warranted.
- **P1 — High:** likely causes a security boundary violation, corrupted persistent data, broken primary workflow, or major outage; block merge.
- **P2 — Medium:** causes a concrete functional or operational regression in a narrower but realistic scenario; fix before normal release.
- **P3 — Low:** causes a bounded correctness or maintainability defect with real impact; fix when touching the area. Do not use P3 for style.

Lower severity when impact requires unlikely preconditions. Omit a candidate when both reachability and impact remain speculative.

## Finding schema

Write each finding in this form:

```markdown
### [P1] Imperative, specific title

- Location: `path/to/file.ext:line`
- Evidence: What changed and the concrete reachable path to failure.
- Impact: Who or what is affected and how.
- Correction: The smallest safe direction; do not prescribe an unverified rewrite.
- Verify: The focused test or command that would prove the correction.
```

Use a line range only when one line cannot identify the defect. Include a confidence note only when it materially qualifies the evidence.

## Clean review schema

When no finding survives validation, return:

```markdown
No actionable findings.

Residual verification gaps:
- <only material unrun or unavailable check, or `None`>
```

Never replace findings with a prose summary. Put any brief summary after the findings.
