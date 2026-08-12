# Web, API, authentication, and database profile

Load this reference when direct evidence shows a browser UI, HTTP/RPC API, authentication boundary, persistent database, schema, or migration system.

## Detect boundaries

- Identify browser entrypoints, routes, server handlers, serializers/schemas, middleware, and public API specifications from source and configuration.
- Identify authentication and authorization enforcement points, tenant/workspace identifiers, session or token handling, and trusted proxy boundaries.
- Identify database engines, ORM/query layers, migrations, transaction boundaries, seed/fixture paths, and destructive maintenance commands.
- Distinguish confirmed runtime wiring from unused dependencies or example files.

## Route context

Record the product-facing route or flow, owning component, data touched, trust boundary, and closest tests. Add path/topic routes for UI, API contracts, authorization, data model, testing, and release/migration documents only where relevant.

Tag risks such as `public-api`, `authorization`, `tenant-isolation`, `sensitive-data`, `persistent-state`, `migration`, `payment`, `idempotency`, or `lifecycle` only with direct evidence.

## Select gates

- Use component tests for observable browser behavior when configured.
- Use integration/API tests for routing, validation, authorization, serialization, persistence, and transactions.
- Use focused end-to-end tests only when the browser/runtime integration is itself the contract.
- Connect migration validation, schema drift, downgrade/rollback, and authorization checks only when the repository provides a safe deterministic command.
- Never point required checks at a production database or real identity/payment provider.

Document migration and rollback commands as operationally sensitive. Discovery does not authorize applying migrations, using real customer data, or changing production state.
