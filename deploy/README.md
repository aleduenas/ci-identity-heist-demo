# Deployment assets

`kubernetes/base/` separates workload, namespace, network controls and employee/release RBAC. `generated/` is ignored and receives operator-specific rendered manifests. The base is a template: never apply its `__...__` placeholders directly.

Follow [the delivery runbook](../docs/delivery.md) for bootstrap, runner setup, daily deployment and access verification. Infrastructure and identity are managed separately; cluster credentials remain outside repository configuration and manifests.
