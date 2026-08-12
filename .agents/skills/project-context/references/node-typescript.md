# Node and TypeScript profile

Load this reference only when repository evidence contains a Node or JavaScript/TypeScript component.

## Detect

- Treat `package.json` as the manifest. Read `packageManager` first, then use the committed lockfile to select npm, pnpm, Yarn, or Bun.
- Detect workspaces from the manifest, `pnpm-workspace.yaml`, or the selected package manager's workspace configuration. Do not infer a monorepo from multiple directories alone.
- Record TypeScript only when `tsconfig*.json`, TypeScript source, or a declared TypeScript dependency exists.
- Inspect package scripts, test configuration, framework configuration, and CI before choosing canonical commands.

## Select canonical commands

Prefer checked-in scripts such as `format:check`, `lint`, `typecheck`, `test`, `test:integration`, and `build`. Invoke them through the selected package manager; do not substitute a globally installed tool.

Use the matching reproducible install only when dependency installation is required:

- npm: `npm ci`
- pnpm: `pnpm install --frozen-lockfile`
- Yarn: `yarn install --immutable`
- Bun: `bun install --frozen-lockfile`

Do not run multiple package managers against one component. If lockfiles conflict, record a user decision instead of choosing silently.

## Record gates and context

- Mark an existing, relevant lint/type/test/build command `required` when it protects shipped behavior.
- Mark a useful but non-blocking command `optional` with its purpose.
- Mark a category `not_applicable` only with evidence, such as a JavaScript-only package for typechecking.
- Never invent a missing script or claim a framework default command is canonical.
- Route source paths to the component's architecture, test, and release context. Tag browser, API, database, or AI risks only when direct evidence activates them.

Exclude `node_modules`, build output, caches, coverage output, and values from environment files from generated context.
