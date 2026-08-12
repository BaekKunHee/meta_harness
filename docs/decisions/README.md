# Architecture decision records

Use an ADR for durable choices that affect more than one change: public
contracts, component boundaries, data ownership, trust and authorization,
dependencies, migrations, operational policy, or deliberate tradeoffs.

Copy `0000-template.md` to the next four-digit number and a short kebab-case
title, for example `0001-choose-primary-database.md`. Do not renumber accepted
records.

Statuses are `Proposed`, `Accepted`, `Superseded`, or `Rejected`. A changed
decision creates a new ADR and links to the superseded one; history is not
rewritten. Record evidence separately from assumptions and unresolved follow-up.

An ADR explains why a decision exists. It does not replace executable config,
schemas, tests, or the component inventory in `.harness/project.json`.
