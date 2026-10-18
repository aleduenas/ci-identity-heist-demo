# Demo verification status

Updated: 2026-10-18. [DEMO.md](../DEMO.md) defines the current flow.

## Current environment

Read-only checks against the owned sandbox and GitHub confirmed:

- AWS region `us-east-1`; EKS 1.35 is `ACTIVE` with both public and private API access.
  Public control-plane access is intentional for the GitHub-hosted attack runner.
  Worker nodes and the application Service remain private.
- The application Deployment has two desired, ready and available replicas and uses an ECR digest.
- GitHub repository visibility is private. Its main release runner is online and deployment is enabled.
- The coordinated immutable OIDC subject includes repository, context, event, run ID and attempt.
- The isolated detection role currently permits PR-context assumption for the demo;
  the baseline release identities remain main-only.
- A refreshed Terraform plan reports **no changes** with the reconciled local settings.
  The outdated local `enable_d2` key was migrated to `enable_detection`, avoiding deletion of
  the exercise roles. Retained audit/ECR storage remains protected against automatic deletion.

Those observations describe the pre-control sandbox review; no rebuild was required.
The additional security automation role below is prepared but not yet provisioned.

## GitHub-deployed control, 2026-10-18

- `security/control.json` is the versioned setting; it currently remains `false`
  for the successful-attack portion of the synthetic demonstration.
- `Deploy security control` runs only on main push/manual events and calls the
  self-contained `scripts/detection/apply_control.py` directly through IAM.
  It prints before/desired/saved policies and verifies readback. A separate job
  proves main can still obtain the same exercise role.
- Initial provisioning defines a separate main-only automation role with only
  `iam:GetRole` and `iam:UpdateAssumeRolePolicy` on the exact exercise role.
  A real refreshed setup plan contains **2 additions, 0 changes, 0 deletions**:
  that role and its inline policy. No apply was performed for this change.
- Initial Terraform provisioning and the workflow read the same committed setting.
  The old root `allow_pr_demo` input is compatibility-only; the local Terraform
  prevention command is retired. **No Terraform runs during the demo.**
- Read-only inspection confirmed the live exercise trust matches the script's
  expected permissive policy and the repository uses the expected immutable OIDC
  subject. Main branch protection was absent at inspection; no protection setting
  was changed or claimed as configured.
- Local verification: **103 pytest tests**, **6 delivery tests**, Ruff, actionlint,
  Terraform formatting and backend-free validation of both roots passed. The new
  tests exercise both trust transitions, unexpected policy rejection, readback
  failure and PR/main workflow boundaries. Publication hygiene reported no findings.
- Pending initial setup: apply the reviewed role/policy plan, set the two new
  repository variables, and rehearse the GitHub workflow. No live control activation,
  PR denial or harmless retry is claimed for this new workflow yet.

## Recorded detection evidence

The [2026-10-17 evidence](detection/evidence.md) records main-context classification,
PR credential misuse with an observed 31.1-second detection time, PR denial after tightening
trust, and an explicit missing-context result. That run used a different, private-endpoint
historical environment and did not establish deployment mutation or customer-record access.
Current application readiness does not prove the full attack has been rerun.

## Repository review

- The interview brief, draft write-up and outdated agent instructions are excluded from future
  commits. Local copies of planning material remain in ignored storage.
- Local assistant settings, AWS configuration, credentials, state, plans, generated identities
  and generated evidence are ignored. Docker receives only application source and its manifest.
- A focused credential-pattern scan of all 395 reachable historical blobs found no matches.
  This checks recognizable token/key/JWT formats; it is not a guarantee that arbitrary secrets
  cannot exist. Previously committed internal documents remain in Git history.
- CI now checks publication hygiene. The check prints paths and rule names, never matched values.
- Documentation distinguishes private application access from the public EKS control-plane API,
  and current observations from historical acceptance results.

## Validation

Ruff, application/identity/detection tests, delivery contract tests, Terraform formatting and
backend-free validation of both roots are required by [testing](testing.md). Results: **85 pytest tests passed**, **6 delivery tests passed**, Ruff and Terraform formatting
passed, and both roots passed backend-free validation with checksum-verified provider caches.
The Docker build and isolated Compose smoke passed readiness, authentication, atomic transfer,
idempotency, conflict rejection and overdraft rollback. All local documentation links resolved;
no Python or Terraform source file exceeded 150 lines. The publication guard reported zero findings.

## Remaining boundaries

- The attack payload and attack workflow were left unchanged during this review. This audit did not
  rerun the attack, prevention toggle, data extraction or application replacement.
- SAML federation and live network-policy enforcement were not exercised during this review.
- Existing attack-related GitHub settings, including legacy `D2_*` variables, were left unchanged.
- Removing files from current commits does not erase previous GitHub history; historical internal
  documents remain until a separately coordinated history cleanup.
