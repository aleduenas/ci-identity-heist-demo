# Identity module

Application Pod Identity binds only `mybank/mybank-api`. It can fetch records from the three tables (readiness probes use GetItem), and update accounts plus insert transfers only inside `TransactWriteItems`. No customer writes, table scans, deletes, or schema administration are granted. IAM guards API operations; the application enforces immutable ledger conditions and business invariants.

Federation is disabled until `saml_metadata_path` points to real exported metadata. The prospective configuration output remains available for realm generation. On the second apply, a provider and SAML-only engineer/support roles are created. Engineers describe EKS and join `mybank:engineers`; namespace permissions are managed separately in Kubernetes. Support can read all three synthetic tables and cannot write them or enter EKS. Role sessions last at most one hour. Metadata must contain the live IdP signing certificate; rotating that certificate requires updating the provider.
