# D2 live evidence — 2026-10-17

Sanitized summary of the live D2 exercise in the owned sandbox (account `404824402451`, `ca-central-1`, private repository `aleduenas/mybank-eks-sandbox`). Raw collector output stays in ignored `docs/d2/generated/`; it holds only allowlisted fields (no JWT, credentials object, access-key ID or session token). All records, repository and identities are synthetic or lab-owned. Nothing here measures the later EKS-change, data-read or exfiltration steps of the concept.

## Setup actually observed

| Item | Observation (UTC) |
| --- | --- |
| Sandbox apply | 65 resources created; EKS 1.35 `ACTIVE`, public endpoint `false`, 2 nodes, 4 add-ons `ACTIVE`, operations host SSM `Online` |
| GitHub OIDC template | Changed from `use_default=true` to `repo, context, event_name, run_id, run_attempt` (immutable subjects retained) together with `MYBANK_OIDC_RUN_CONTEXT=true` |
| Emitted subject | Release check [run 39056882803](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/39056882803) decoded `repo:aleduenas@54992507/mybank-eks-sandbox@1416500552:ref:refs/heads/main:event_name:workflow_dispatch:run_id:39056882803:run_attempt:1` — exactly the template the trust and detector expect |
| Exercise role | `mybank-sandbox-d2-demo-deploy`; A2 trust allowed main push/dispatch **and** `pull_request`; B2 trust main-only |
| Mock agent | `mybank-sandbox-d2-mock-agent` assumed by operator: `eks:DescribeCluster` allowed; `UpdateNodegroupConfig`, `CreateAccessEntry`, DynamoDB `ListTables`/`Scan`, and `sts:AssumeRole` into the deploy role all **denied** |

## Comparisons

| Test | GitHub run | AWS event time | CloudTrail event ID | Independent decision | Observed log delay | Observed TTD |
| --- | --- | --- | --- | --- | --- | --- |
| N2 main dispatch | [39057140370](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/39057140370) | 18:13:31Z | `10fd7b2b-c096-433c-a7b3-95dbd42a4e7e` | `expected_release`, no alert | 72.1 s | — |
| A2 unreviewed PR [#10](https://github.com/aleduenas/mybank-eks-sandbox/pull/10), session name `release-looking-demo` | [39057194544](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/39057194544) | 18:14:12Z | `d7b2b955-bc20-4bf0-a28f-e5d51e0ac6b8` | **`pr_role_misuse`** → alert “Deployment credentials issued to PR validation” | 30.8 s | **31.1 s** |
| B2 PR repeat, main-only trust | [39057413125](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/39057413125) (job failed `AccessDenied`) | 18:17:14Z | `ba46d7c4-eee2-4dce-9f91-e76657f6135a` | `assumption_denied`, linked to PR run by rejected subject | n/a (collected after the fact) | — |
| B2 main repeat | [39057409655](https://github.com/aleduenas/mybank-eks-sandbox/actions/runs/39057409655) | 18:17:12Z | `87ae55d5-4437-461e-beaa-1db21bd218a6` | `expected_release` | 82.9 s | — |
| Context gap (A2 window, GitHub lookup deliberately unavailable) | — | 18:13:31Z, 18:14:12Z | as N2/A2 | both `context_not_verified` → “investigate” notice, never a trusted release | — | — |

Delays are observed values from one collector polling every 15 s, starting 2 minutes before N2. They include polling granularity and are not CloudTrail service guarantees. Three samples do not establish a production false-positive rate or a latency distribution.

## What the evidence shows

- **Detection:** AWS issued the deployment-capable exercise role to unreviewed PR code. The independent collector linked the AWS-accepted signed subject to GitHub's own run-attempt record and alerted within about 31 s of the event. The release-looking session name had no effect.
- **Legitimate case:** both main comparisons were classified `expected_release` with no alert.
- **Prevention (B2):** removing only the PR subject from the exercise role's trust made AWS deny the PR request while main still succeeded.
- **Visibility gap:** with independent context unavailable, the detector reported `context_not_verified` and did not assume trust.

## Finding fixed during the live run

The fixtures had assumed denied `AssumeRoleWithWebIdentity` events carry `requestParameters.roleArn`. Live CloudTrail records a denial with `requestParameters` and `responseElements` both **null**. The role appears only in `resources[]` (`AWS::IAM::Role`), and the rejected subject in `userIdentity.userName`. The collector therefore dropped denials at first. The collector and detector now read the role from `resources` and link denials through the rejected subject. A regression test reproduces the observed shape.

## Limitations

- The collector used the operator's existing GitHub credential, held in memory in a separate trusted process, instead of a dedicated `Actions: read` token. Provenance is still independent of PR code, but the detector identity was not least-privilege.
- `GetCallerIdentity` proves which identity was issued. The exercise role also had a real `mybank:deployers` EKS access entry, but no Kubernetes call was made and the application was not rolled out (handoff §7D not performed). The private runner, image publish and SAML federation were not exercised.
- No later attack steps (deployment change, data read, egress) were attempted or proven.
