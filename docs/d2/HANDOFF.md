# D2 sandbox: ongoing handoff and completion checklist

**Last checked:** 2026-10-17, 17:19 UTC / 1:19 p.m. America/Toronto.  
**Current stopping point:** CLI authentication, Terraform-state/bootstrap resources and a plain USD20 email budget alert are live. The full EKS/D2 environment has a reviewed saved plan but **has not been applied**. The user requested this handoff to conserve session usage. Do not interpret local implementation or a saved plan as deployed infrastructure.

This is the working checklist for future sessions and agents. Mark an item complete only after its stated result is observed. Add evidence, UTC time and any limitation to the session log at the end. Preserve completed history; explain reversals or revalidation rather than silently changing their meaning.

## 1. User intent and source of truth

- [x] User authorized complete D2 setup in their AWS sandbox and the existing private GitHub repository, including mock identities and eventual live validation.
- [x] Interpret “scenario 2” as **D2: detect PR-validation jobs obtaining deployment-role credentials**.
- [x] User explicitly requested CLI access first; local CLI and SDK authentication now work.
- [x] A normal USD20 monthly budget email alert is in place (see §2).
- [ ] Finish the full private AWS application environment and GitHub delivery; do not shrink the user's full-environment request to a mock-only detection demo.
- [ ] Create the mock-agent IAM role when the sandbox is applied. No fake AI application, real infostealer, or fake employee is required. An IAM role cannot push GitHub PRs: document the operator-authored PR as the simulated stolen-agent action.

Read [AGENTS.md](../../AGENTS.md), [architecture](../architecture.md), [implementation status](../implementation-status.md), this file, and the [D2 runbook](README.md) before continuing.

The [original concept](../plan/Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md) is **immutable**. Keep its full chain, assumptions, D1–D4 options, D3 recommendation and conditional D2 fallback intact. The user subsequently authorized implementing D2; that does not authorize rewriting their concept. The [take-home instructions](../plan/take_home.md) are also unchanged. The second attack path remains explicitly deferred by the user. Use synthetic records only; do not interact with real Relay infrastructure, domains or employees. Keep EKS and the application private.

Source SHA-256 values verified before implementation:

| Source | SHA-256 |
| --- | --- |
| `docs/plan/take_home.md` | `5EDE87CBF19670903D7795B55383BD4A10EF1FC6CA58FACBA2893159E8D09352` |
| Original concept in `docs/plan/` | `0D959B26B6D2F1CC2F0CE3BA2960A40CFCB544F2C18B7D70EED4F2626FD7D12A` |

## 2. Budget alert

- [x] Plain account budget `mybank-sandbox-monthly-usd20` (USD20/month, managed by the bootstrap root) emails the operator when actual spend exceeds 100%. Alert only.
- [x] The user's existing `test budget` is untouched.

AWS Budgets data is delayed. EKS, NAT and storage keep costing until the lab is torn down per [teardown](../teardown.md); stopping nodes does not stop EKS/NAT charges. Watch spend and tear down promptly after the exercise.

## 3. Verified environment and access

| Item | Current value/status |
| --- | --- |
| Workspace | `C:\Users\icybe\Documents\mlprojects\relay` |
| AWS account / Region | `404824402451` / `ca-central-1` |
| Verified caller | `arn:aws:iam::404824402451:user/codex-builder` — this is an IAM **user**, despite the initial description as a role |
| Existing caller policies | `AdministratorAccess`, `SignInLocalDevelopmentAccess` |
| Repository | `aleduenas/mybank-eks-sandbox`, private, default branch `main` |
| GitHub IDs | owner `54992507`, repository `1416500552` |
| Git HEAD at handoff | `61fcdad6c7cf7990ee8e1eaa34436342f52228a2` |
| GitHub OIDC live setting | `use_default=true`, `use_immutable_subject=true`; custom run context **not configured** |
| Live repository variables | Empty, verified through GitHub API; publishing/deployment remain gated off |
| Live EKS clusters in target Region | None, verified at handoff |

### CLI and SDK access

AWS CLI **2.38.1** was extracted locally from the official Amazon-signed installer. The Session Manager plugin was extracted from the official AWS ZIP; its executable signature is valid. No long-lived API key was created. AWS CLI and boto3 both successfully called STS as the caller above.

From the workspace root:

```powershell
.venv/Scripts/python.exe -m scripts.aws.run aws sts get-caller-identity
```

The wrapper sets repository-local AWS configuration, login-cache paths, CLI/plugin PATH and process-credential profile. For an interactive PowerShell session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. ./scripts/aws/session.ps1
aws sts get-caller-identity
# If temporary login expired:
aws login --profile codex-builder-login --remote --region ca-central-1
```

The execution-policy change affects only that process. Login uses the console session and the **verification code displayed by AWS**, not the raw `code` URL parameter. Browser use should be limited to necessary login; provisioning uses CLI/SDK. Never print tokens, passwords, authorization codes or cached credential contents. Temporary sessions may need renewal; do not assume they survive into another session.

The supplied `codex-builder_credentials.csv` contains console username/password/sign-in URL, not access keys. It is now ignored. `.cache/`, `.tools/`, `.playwright-mcp/`, state/plans and generated D2 evidence are also ignored. Do not add any of them to Git.

GitHub API auth works through Windows Git Credential Manager and [the helper](../../scripts/github/client.py); no token is stored by that helper. Read operations succeeded only outside the restricted filesystem process. If it fails with `wincredman`/terminal-prompts-disabled errors, request the normal tool sandbox escalation for the authorized command; do not print `git credential fill` output. GitHub CLI is not installed and is not required. The detector's eventual least-privilege `Actions: read` credential remains to be arranged; do not give it to PR jobs.

## 4. Resources actually deployed

### State and Kubernetes bootstrap identity: applied

- [x] Created private encrypted/versioned state bucket `mybank-tf-state-404824402451-ca-central-1` with TLS enforcement and public-access blocking.
- [x] Created `arn:aws:iam::404824402451:role/mybank-sandbox-bootstrap`, trusted only by the explicit operator user. Its IAM policy allows describing this lab cluster; Kubernetes administration is granted later by the planned EKS access association, not by broad AWS AdministratorAccess on this role.
- [x] Bootstrap apply created **7 resources**. Bootstrap now validates the allowed account ID.
- [x] Initialized sandbox S3 backend, key `sandbox/terraform.tfstate`, native S3 lockfile enabled.
- [x] Bootstrap apply later added the USD20 email budget (1 create).
- [ ] Do not delete local bootstrap state. This root intentionally has independent local state and is not removed with lab compute.

### Full sandbox: only planned

The saved plan has **65 creates, 9 data reads, no changes/destroys**. It includes private EKS 1.35 (AWS API confirmed standard support), two on-demand workers, operations host, NAT/EIP, ECR, three synthetic DynamoDB tables, auditing, Pod Identity, baseline build/deploy roles and isolated D2/mock roles. The EKS API is private; public endpoint is false.

The exact main/PR role and image access still require live validation. No paid EKS/EC2/NAT lab resources, application rollout, runner registration, fixture seeding, actual GitHub role assumption, or detection result has occurred.

## 5. Local files and state needed to resume

| Path | Purpose and handling |
| --- | --- |
| `.cache/aws/config`, `.cache/aws/login/` | Temporary login/process profile; secrets stay ignored |
| `.tools/aws-cli/portable/Amazon/AWSCLIV2/aws.exe` | Verified CLI executable |
| `.tools/session-manager/portable/bin/session-manager-plugin.exe` | Verified private-access plugin |
| `.tools/terraform/terraform.exe` | Terraform 1.13.5 from previous setup |
| `.cache/bootstrap.tfvars.json`, `.cache/bootstrap.tfplan` | Bootstrap inputs (includes alert email) and historical applied plan |
| `infra/bootstrap/terraform.tfstate` | Actual state-bucket/bootstrap-role state; protect and retain |
| `infra/environments/sandbox/backend.hcl` | Ignored live S3 backend configuration |
| `.cache/sandbox.tfvars.json` | Intended full deployment inputs, including D2 and custom OIDC mode |
| `.cache/sandbox.tfplan`, `.cache/sandbox-plan.log` | **Not applied**; saved full plan/review log; replan before applying |
| `docs/d2/generated/` | Ignored mock/live evidence; existing mock output is not a live result |

Current intended sandbox inputs: name `mybank-sandbox`, Region `ca-central-1`, account above, bootstrap role above, `enable_d2=true`, `allow_pr_demo=true`, `github_oidc_include_run_context=true`, mock principal equal to the operator user ARN. `allow_pr_demo=true` applies only to the isolated demo role; baseline release roles remain main-only. Read the actual ignored file before reuse.

## 6. Implementation already written, not yet committed/pushed

- [x] CI infrastructure checks validate both Terraform roots.
- [x] `scripts/aws/`: local CLI/session helpers; `scripts/github/`: authenticated operator API helper.
- [x] `infra/bootstrap/operator.tf` plus account validation: narrow explicit bootstrap identity.
- [x] `infra/modules/d2/` and sandbox `d2*.tf`: disabled-by-default module, separate exercise deployment role and optional mock-agent role.
- [x] `scripts/d2/`, `tests/d2/`, `.github/workflows/d2-demo.yml`: harmless identity probe, independent collector, detector, replay and report.
- [x] Coordinated optional baseline subject migration in delivery module, sandbox variables/access, release workflow and `scripts/checks/oidc_claims.py`.
- [ ] Review, commit and push appropriate source changes. All work from this deployment session is still local. `docs/plan/` is also untracked from earlier drafting; preserve the author's source and do not stage credentials/generated artifacts by using a blanket add.
- [ ] Update component docs for changed bootstrap inputs and subject-output semantics before committing.

Baseline `github_oidc_subject` now returns the first accepted subject/pattern; `github_oidc_subjects` returns the list. Custom mode is opt-in in code; the ignored intended deployment enables it. The checker verifies decoded format only, not an independent JWT signature or AWS acceptance.

## 7. Remaining checklist, in execution order

### A. Resume and protect the account

- [ ] Read this handoff and current Git diff; preserve uncommitted work from all agents.
- [ ] Authenticate via CLI and verify caller/account.

### B. Finish repository integration and coordinated OIDC setup

- [ ] Run/review checks in §8; fix genuine failures before pushing. No new hosted CI has run for this work.
- [ ] Review and commit only intended code/docs; confirm ignored secrets/state/generated files remain excluded and repo remains private.
- [ ] Prepare baseline main-only custom subject trusts and the isolated exercise role together. The current live GitHub template is still the old default.
- [ ] Set the repository OIDC template to `{"use_default":false,"include_claim_keys":["repo","context","event_name","run_id","run_attempt"]}` and record the previous setting for coordinated restoration.
- [ ] Set repository variable `MYBANK_OIDC_RUN_CONTEXT=true` for the migrated release checker. Confirm the actual emitted subject matches the intended immutable prefix and template; do not guess.
- [ ] Never broaden baseline build/deploy roles to PRs. Intended prefix is `repo:aleduenas@54992507/mybank-eks-sandbox@1416500552`.

### C. Provision the full private sandbox

- [ ] Replan using current inputs; review resources, private endpoints, identity scopes and standard-support version. Do not blindly apply the old saved plan after drift.
- [ ] Apply the full root; retain new real outputs in ignored `.cache/outputs.json`.
- [ ] Verify EKS ACTIVE, nodes/add-ons healthy, operations host SSM Online, runtime identity association and database endpoint/routing.

Suggested local commands, after checking current inputs:

```powershell
.venv/Scripts/python.exe -m scripts.aws.run .tools/terraform/terraform.exe '-chdir=infra/environments/sandbox' plan '-input=false' '-var-file=../../../.cache/sandbox.tfvars.json' '-out=../../../.cache/sandbox.tfplan'
# Review before executing this authorized operator step:
.venv/Scripts/python.exe -m scripts.aws.run .tools/terraform/terraform.exe '-chdir=infra/environments/sandbox' apply '-input=false' '../../../.cache/sandbox.tfplan'
```

Quote Terraform arguments containing paths/equals signs in Windows PowerShell; unquoted arguments produced “Too many command line arguments” in this session. The wrapper supplies AWS auth to Terraform and child SDKs. Standard PowerShell redirection can write UTF-16; write Terraform JSON outputs using Python/explicit UTF-8 instead.

### D. Make the normal application and release path work

- [ ] Configure `AWS_REGION`, `AWS_BUILD_ROLE_ARN`, `ECR_REPOSITORY_URL` from real outputs. Keep `DEPLOY_ENABLED` off until bootstrap/runner are ready.
- [ ] Push/dispatch a trusted main release; validate OIDC format/actual AWS assumption, publish the immutable image and retain its digest.
- [ ] Install missing AWS CLI/kubectl on the private operations host and register the trusted GitHub runner. Existing user-data does not perform those steps. Keep registration tokens out of Git, command logs and evidence.
- [ ] Use the installed Session Manager plugin and [private-access runbook](../private-access.md) to reach private EKS; keep bootstrap credentials on the workstation.
- [ ] Render and bootstrap namespace `mybank`, Deployment/Service/ServiceAccount `mybank-api`, policies and externally generated API-key Secret using existing scripts.
- [ ] Seed only synthetic records and verify readiness, authenticated transaction, idempotent retry, conflict and overdraft rollback.
- [ ] Verify engineer/deployer restrictions and actual CNI enforcement. A manifest or admin impersonation check alone is not proof.
- [ ] Configure `AWS_DEPLOY_ROLE_ARN`, `EKS_CLUSTER_NAME`; enable deployment only after first bootstrap and runner acceptance. Prove one normal main release.
- [ ] Explicitly decide/record whether optional employee SAML federation is needed for this D2 acceptance; it is not currently enabled and must not be claimed as tested.

### E. Exercise D2 and collect independent evidence

- [ ] Confirm the same isolated `mybank-sandbox-d2-demo-deploy` role is used for N2/main and A2/PR, with real namespace deployer access. Its IAM permissions alone do not prove network reachability.
- [ ] Set repository variable `D2_DEMO_ROLE_ARN` to its real output. Use hosted runners only for the PR identity probe; do not expose the private runner or cluster endpoint.
- [ ] Assume/inspect the mock-agent role and prove no direct customer-table/deployment bypass. Keep the GitHub simulated actor distinction explicit.
- [ ] Arrange a separate read-only GitHub collector credential and trusted execution checkout/process. The operator API helper's broad credential is not a demonstrated least-privilege detector identity.
- [ ] Start collector polling **before** running comparisons; use actual UTC start/end, regional STS and CloudTrail lookup. Keep raw credentials/JWT/sessionToken fields out of retained events.
- [ ] N2: dispatch main exercise job; prove role issuance and independent `expected_release` classification.
- [ ] A2: operator creates an open, unreviewed same-repo PR and changes the harmless marker in `scripts/d2/demo_probe.py`; prove pre-review execution, successful same-role issuance and independent `pr_role_misuse` alert.
- [ ] Confirm release-looking session naming cannot fool the detector. Its linkage is AWS's accepted signed subject plus independently fetched GitHub run/attempt metadata.
- [ ] Verify actual CloudTrail provider/audience/subject field shapes. The proposed custom subject and collector assumptions have not yet been demonstrated live.
- [ ] Test missing/mismatched context yields `context_not_verified`, not an invented trusted release.
- [ ] Optional B2: remove PR trust only from the exercise role, repeat PR and main; prove PR denial and continued main success. Record this as separate prevention evidence.
- [ ] Produce sanitized report with action/log/alert times, observed detection/ingestion delay, limitations and legitimate-case behavior. Do not infer production rates or full-chain success.

The live runbook includes collector/report commands. Use `D2_GITHUB_TOKEN` only in the trusted operator process, loaded without printing/storing it. The planned proof stops at harmless STS identity checks; it does not require a malicious container or exfiltration. Complete the normal backend environment for the user's requested context, while keeping later attacker actions untested unless separately exercised.

### F. Finish, retain evidence and stop costs

- [ ] Update this checklist, [implementation ledger](../implementation-status.md), D2 runbook and AI note with actual observations and remaining gaps.
- [ ] Prepare the final short assignment artifact/write-up separately from detailed planning docs; second path remains deferred until the author resumes it.
- [ ] Disable/remove exercise variables and PR-role trust when no longer needed. Restore OIDC settings, baseline trust and checker **together** if reverting the template.
- [ ] Preserve selected sanitized evidence, then tear down lab compute/network using [teardown](../teardown.md); keep state until cleanup is verified.
- [ ] Verify node groups/cluster, EC2, NAT and EIP removal, and inventory retained tables, images, volumes, logs and S3 versions. Report ongoing residual costs.
- [ ] Reconcile Terraform drift/state, runner registration, tokens and temporary login. Do not erase state before destroying resources.

## 8. Verification snapshot and tool caveats

| Check | Observed result |
| --- | --- |
| `ruff check app tests identity scripts` | Passed |
| `pytest tests` | **67 passed**, one existing Starlette/HTTPX deprecation warning |
| Delivery unittest discovery | **6 passed** outside the filesystem sandbox |
| Terraform formatting | Passed recursively |
| Terraform validation | Bootstrap and sandbox roots passed |
| D2 unit tests | 22 tests, included in the 67; mock replay is not live proof |
| OIDC format tests | 13 tests, included in the 67 |
| AWS full-lab apply / GitHub new CI / N2-A2-B2 | **Not performed** |

`kubectl kustomize` could not resolve the workspace directory inside the restricted process (“Access is denied”). The identical delivery tests passed with normal tool escalation; do not change security manifests to work around that tool restriction. Terraform provider initialization also needed escalation for Windows Temp access. Downloads were verified before extraction. Docker daemon access was denied in the restricted process; no new container smoke was completed in this session.

## 9. Session log — append on every continuation

| UTC/date | Agent/session | Completed and evidence | Next step / limitations |
| --- | --- | --- | --- |
| 2026-10-17, through 17:19 UTC | Initial live setup | Temporary CLI/SDK auth; state/bootstrap apply; full sandbox planned; tests and delivery checks passed | User requested handoff before further provisioning. Full lab not applied, GitHub unchanged, code uncommitted. Replan and apply the full sandbox next |
| 2026-10-17, later | Budget alert | Plain USD20 email budget added via bootstrap root; 67 tests, Ruff, fmt and validation pass | Replan and apply the full sandbox |
| TBD | Next session | Add completed checkbox IDs/section, resource/run IDs, UTC and sanitized evidence | Record blocker, current spend and concrete next action |
