# Identity module

Application Pod Identity binds only `mybank/mybank-api`. Its configured read actions
are GetItem, BatchGetItem, Query, Scan and DescribeTable on the three synthetic tables.
Readiness needs only GetItem; the broader reads, particularly Scan, are an explicit
lab permission that replacement application code can inherit. The
[attack/control explanation](../../../docs/architecture.md#live-exercise-and-security-control-delivery)
describes this pivot. Do not claim table scans are denied by this policy.
Account updates and transfer inserts are allowed only inside TransactWriteItems.
Customer writes, deletes and schema administration are not granted. IAM constrains
API operations; the application enforces business and immutable-ledger conditions.

Federation is disabled until `saml_metadata_path` points to real exported metadata. The prospective configuration output remains available for realm generation. On the second apply, a provider and SAML-only engineer/support roles are created. Engineers describe EKS and join `mybank:engineers`; namespace permissions are managed separately in Kubernetes. Support can read all three synthetic tables and cannot write them or enter EKS. Role sessions last at most one hour. Metadata must contain the live IdP signing certificate; rotating that certificate requires updating the provider.
