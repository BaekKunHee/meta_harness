# Security policy

## Default operating boundary

Repository-local, reversible development and verification may proceed
autonomously. Explicit human confirmation is required immediately before:

- deploying or changing a production or shared live environment;
- sending an external message or mutating an external system;
- reading or using real personal, customer, credential, or production data;
- creating a paid resource or materially increasing cost;
- expanding permissions, weakening a security control, or exposing a service;
- applying an irreversible migration or broadly deleting data or resources.

Authorization for analysis or implementation does not imply authorization for
these side effects. Prefer previews, dry runs, test fixtures, local emulators,
and reversible changes.

## Secrets and sensitive data

- Never commit credentials, tokens, private keys, production exports, or personal data.
- Treat `.env` files as sensitive. The harness must not read them.
- From `.env.example`, tools may use variable names only; values must not enter
  generated context, logs, fixtures, or reports.
- Redact secrets from command output and handoffs. Rotate a secret if exposure is suspected.
- Use synthetic or irreversibly anonymized fixtures by default.

## Security verification

Run `scripts/check security` for changes involving authentication,
authorization, untrusted input, cryptography, dependencies, workflows,
infrastructure, data boundaries, or release controls. Security checks complement
focused contract tests; they do not replace them.

The repository-local gate checks harness drift, secret and personal-path leaks,
and workflow policy. The GitHub security workflow additionally runs OSV against
lockfiles and a pinned Trivy filesystem scan for secrets and configuration
mistakes. CodeQL and dependency review remain host/repository-plan setup until
their availability is verified.

For a suspected vulnerability, preserve evidence without exploiting unrelated
systems, identify the affected trust boundary, and provide a minimal safe
reproduction. Do not open a public issue containing sensitive details. Use the
repository owner's private reporting channel once one is configured; until
then, stop before disclosure and ask the owner for the approved channel.
