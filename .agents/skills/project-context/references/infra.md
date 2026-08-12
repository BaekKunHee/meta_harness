# Infrastructure profile

Load this reference only when Terraform, Kubernetes, or Helm files are actually present. Infrastructure discovery is read-only and does not authorize a live change.

## Detect

- Terraform: inspect roots, modules, provider/version constraints, backend declarations, lockfiles, variable declarations, and CI commands.
- Kubernetes: inspect manifests, overlays, namespaces, cluster/context documentation, policy files, and deployment tooling.
- Helm: inspect charts, dependencies, values layers, schemas, release commands, and rendered-manifest checks.
- Distinguish examples and vendored modules/charts from deployed sources.

## Select safe gates

Use only commands supported by repository configuration, such as format checks, static validation, linting, schema validation, Helm rendering, or server-side/client dry runs that cannot mutate shared state.

Do not run `terraform apply`, state mutation/import, `kubectl apply/delete/rollout`, Helm install/upgrade/uninstall, secret decryption, or any production command during initialization, refresh, or routine checks. A speculative `terraform plan` can still contact providers or expose sensitive state; require the repository's approved offline or isolated workflow.

## Route context and report gaps

Record environment ownership, state/backend boundary, deployment source, namespace/account/region selection, secret mechanism, validation command, rollout signal, and rollback procedure only when confirmed.

Tag `infrastructure`, `production-boundary`, `credentialed-operation`, `stateful-change`, and `destructive-operation` where applicable. Report missing policy checks, environment protection, drift detection, rollout verification, or rollback evidence as unresolved; never mark them complete from manifests alone.
