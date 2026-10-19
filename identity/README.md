# Employee federation

Local Keycloak is the lab's SAML identity provider. IAM trusts its signing certificate and maps employees into separate engineer and support roles. GitHub Actions uses a separate OIDC trust.

Files are deliberately separated: `keycloak/realm.json` contains realm settings; `keycloak/client.py` declares AWS SAML claims; `generate_realm.py` constructs the account-specific import; `export_metadata.py` exports the live public certificate; `assume_role.py` exchanges your own assertion for temporary CLI credentials. `keycloak/compose.yml` runs the localhost-only development IdP.

Follow [the identity runbook](../docs/identity.md). Generated realm passwords, SAML assertions and temporary credentials belong in ignored `identity/generated/`. Never copy these into tracked documentation. On Windows, keep this directory in your private user workspace; POSIX file modes do not replace Windows ACLs.
