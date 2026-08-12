# AI service profile

Load this reference only when direct evidence shows model calls, prompts, retrieval, embeddings, agent orchestration, tool use, or AI evaluation.

## Detect the system

- Locate model/provider configuration, prompt sources, structured-output schemas, retrieval/index boundaries, tool definitions, safety checks, and eval datasets.
- Trace where untrusted user or retrieved content enters prompts and where model output can trigger tools or persistent side effects.
- Separate deterministic application logic from provider-dependent behavior. Do not infer a live model or capability from an installed SDK alone.

## Route context and risk

Record model configuration ownership, prompt/version ownership, data sent to providers, retention-sensitive inputs, tool approval boundaries, cost/rate-limit behavior, and fallback semantics when confirmed.

Tag applicable risks: `untrusted-model-input`, `prompt-injection`, `sensitive-data`, `external-side-effect`, `paid-provider`, `nondeterminism`, `structured-output`, or `retrieval-boundary`.

## Select gates

- Prefer deterministic contract tests with recorded fixtures, fake providers, fixed clocks/IDs, and schema validation.
- Connect repository evals that run offline and have explicit pass criteria.
- Keep live provider calls out of required default gates. Label opt-in live evals `optional`, with cost, credentials, and data constraints.
- Verify that denied or malformed tool calls cannot create side effects and that retries do not duplicate approved actions.
- Treat eval runner failure, timeout, or invalid output as a failed or unavailable check, never a pass.

Do not copy API keys, prompt secrets, customer content, raw production traces, or personal data into project context.
