# Detection: PR validation obtaining the deployment identity

This implementation evaluates one boundary in the immutable concept: unreviewed PR code obtains the AWS identity intended for deployment. The demonstration uses an intentionally scoped exercise role, a harmless script, and independently collected evidence. It does not execute an infostealer, impersonate a real AI agent, deploy an attacker container, or access customer data. The operator authors the simulated PR. A separately provisioned mock IAM role represents the concept's starting identity; AWS IAM does not itself grant GitHub access.

**Status:** Live-validated 2026-10-17. N2 `expected_release`, A2 `pr_role_misuse` with an observed TTD of about 31 s, B2 PR denial with main still working, and a live `context_not_verified` gap. See the [sanitized evidence](evidence.md). The lab compute was torn down afterwards. The full attack chain (deployment change, data read, egress) remains unproven.

## Components and authority

| Component | Authority and behavior |
| --- | --- |
| `.github/workflows/detection-demo.yml` | Hosted runner only; runs on relevant main changes/manual dispatch and same-repository PR updates |
| `scripts/detection/demo_probe.py` | PR-editable harmless entrypoint; requests exercise credentials and calls `GetCallerIdentity` |
| `scripts/detection/collect.py` | Separate operator-side collection of AWS CloudTrail and GitHub run metadata |
| `scripts/detection/detector.py` | Classifies expected main use, successful PR misuse, denial, or unverifiable context |
| `scripts/detection/replay.py` | Invented offline examples, labeled as fixtures |
| `scripts/detection/alert.py` | Renders the retrievable alert text for `pr_role_misuse` and an investigate notice for `context_not_verified` |
| `scripts/detection/report.py` | Summarizes decisions and observed live delays without inventing timing for fixtures |

The exercise job receives `contents: read` and `id-token: write`. It has no GitHub write token, no private runner, and no detector credential. Its `release-looking-demo` AWS session name deliberately resembles a release. The detector never uses that label to establish provenance.

Keep the collector, its GitHub credential, destination evidence, and authoritative detector checkout outside the PR's control. Run collection from a separate trusted checkout/process. Merely placing a detector file in the same repository is not an independent execution boundary.

## Local check and fixture demonstration

From the repository root in the prepared Python environment:

```powershell
python -m ruff check scripts/detection tests/detection
python -m pytest tests/detection
python -m scripts.detection.replay --output docs/detection/generated/mock.json
python -m scripts.detection.report docs/detection/generated/mock.json
```

Expected fixture decisions are `expected_release`, `pr_role_misuse` despite the release-looking session label, and `context_not_verified` when independent context is absent. The fixture timestamps, repository and account are invented. These commands do not contact AWS or GitHub.

## Live prerequisites and subject migration

Proceed only after the account check passes. The user has authorized the complete private EKS application environment for this exercise; its rollout remains a tracked operator step. The focused detection itself requires only the identity boundary. Use the isolated `${name}-detection-demo-deploy` role exposed through `DETECTION_DEMO_ROLE_ARN`; do not broaden the baseline release role. `GetCallerIdentity` proves the issued identity, not its EKS access.

The immutable repository prefix currently documented by the source repository is:

```text
repo:aleduenas@54992507/mybank-eks-sandbox@1416500552
```

Verify owner ID, repository ID, current OIDC configuration and actual emitted subject before using it. For an already authenticated GitHub CLI, these read-only commands inspect the configuration:

```powershell
gh api repos/aleduenas/mybank-eks-sandbox --jq '{full_name:.full_name,repository_id:.id,owner_id:.owner.id}'
gh api repos/aleduenas/mybank-eks-sandbox/actions/oidc/customization/sub
```

The detector expects this repository-level subject template in this exact order:

```json
{"use_default":false,"include_claim_keys":["repo","context","event_name","run_id","run_attempt"]}
```

For example, the resulting PR subject would end in `:pull_request:event_name:pull_request:run_id:123:run_attempt:1`. The main comparison would contain `:ref:refs/heads/main:event_name:workflow_dispatch:run_id:124:run_attempt:1`, or `event_name:push`. GitHub supplies the run identifiers inside the signed token; AWS's accepted subject is the link to the independent GitHub lookup. Environment-based and other subject structures intentionally return an evidence gap.

**This is a repository-wide OIDC change.** An optional coordinated baseline migration is now implemented locally: `github_oidc_include_run_context=true` enables main-only custom trust, and repository variable `MYBANK_OIDC_RUN_CONTEXT=true` enables the matching release format check. Neither has been activated remotely. Coordinate Terraform trust, GitHub template and checker settings; record previous settings before changing them. Never broaden the baseline deployment role to PRs. Verify the emitted subject rather than relying on this example.

Set `DETECTION_DEMO_ROLE_ARN` as a GitHub repository variable, and retain the existing `AWS_REGION` variable or use the workflow's `us-east-1` default. Initially leave the variable unset until the isolated role and test configuration are ready; the job then skips.

## Independent live collection

Use an authorized AWS operator session with `cloudtrail:LookupEvents`. The probe's role must not receive that permission or the detector's GitHub token. Supply a separate GitHub credential through `DETECTION_GITHUB_TOKEN`, limited to this repository and **Actions: read**. Load it through approved credential handling; do not paste it into a command, save it in evidence, or put it in a workflow/PR.

Start the collector before the comparisons so its polling bounds availability measurements. In PowerShell, after the separate credential has been loaded:

```powershell
$detectionStart = (Get-Date).ToUniversalTime().AddMinutes(-2).ToString('o')
python -m scripts.detection.collect --role-arn $env:DETECTION_DEMO_ROLE_ARN --repository aleduenas/mybank-eks-sandbox --subject-prefix 'repo:aleduenas@54992507/mybank-eks-sandbox@1416500552' --region us-east-1 --start $detectionStart --follow-seconds 900 --poll-seconds 15 --output docs/detection/generated/live.json
```

Here `DETECTION_DEMO_ROLE_ARN` in the local process is the reviewed exercise output, not a secret. The collector uses the regional CloudTrail `LookupEvents` API, follows every returned page, queries only the relevant operation and time window, filters the exact role, and deduplicates event IDs during that invocation. Page requests are spaced to respect the service's two-request-per-second quota. Start a new output file for each independent observation session; restarting the collector resets its in-memory first-observed times.

Use regional STS in `us-east-1`, as the probe does, so collection queries the matching region. CloudTrail Event History can provide these management events without deploying a new trail. If a separate future implementation uses EventBridge, STS assumptions are read-only management events: a normal `ENABLED` rule is insufficient; it needs an active logging trail and `ENABLED_WITH_ALL_CLOUDTRAIL_MANAGEMENT_EVENTS`.

Live CloudTrail records a **denied** request with null `requestParameters`/`responseElements`. The role is then read from `resources[]` (`AWS::IAM::Role`) and the rejected subject from `userIdentity.userName`, so denials are recorded as `assumption_denied` and linked to their run.

For every successful event, the collector obtains `responseElements.subjectFromWebIdentityToken`, checks the expected GitHub provider/audience and issued-role ARN, and fetches `GET /repos/{owner}/{repo}/actions/runs/{run_id}/attempts/{attempt}`. It verifies immutable owner/repository IDs, exact run and attempt, and event type. Main use must also match `.github/workflows/detection-demo.yml` and branch `main`. A PR-linked success produces `pr_role_misuse`; missing, unsupported or conflicting context produces `context_not_verified`. HTTP errors remain visible without echoing credentials or response bodies.

## Live comparisons and retained evidence

| Test | Safe action | Required evidence/result |
| --- | --- | --- |
| N2 | Dispatch `detection-demo.yml` on `main`, or use its relevant main push | Successful STS event; independently matched main run; `expected_release` |
| A2 | In an existing same-repository PR, change only the harmless `MARKER` string in `scripts/detection/demo_probe.py` and push | PR synchronization starts hosted CI; credentials are issued under exercise permissive trust; independent result is `pr_role_misuse` |
| Spoof check | Retain the workflow's `release-looking-demo` session name during A2 | The subject/run evidence still identifies PR context |
| Context gap | Replay missing or mismatched metadata, or observe a genuine collection failure | `context_not_verified`, never an invented trusted match |
| B2 | Separately switch exercise trust to main-only, then repeat PR and main | PR assumption denied; main still succeeds; retain independent evidence where available |

Keep the PR open and unreviewed for A2; do not merge the marker change to manufacture PR provenance. The operator-authored PR simulates use of stolen coding-agent GitHub access; no real credential theft or AI agent is necessary. If AWS denies A2 under existing trust, record a blocked boundary. That is not a successful misuse detection. The workflow may fail in B2 because denial is the intended observation.

The sanitized live file contains AWS event identity, accepted subject, independent GitHub metadata, decision, first observed searchable time and alert availability. It excludes the entire STS credentials object, raw JWT, access-key ID and session token. Raw API records remain only in collector memory. Generated directories are ignored; review sanitized excerpts before deliberately committing any evidence elsewhere.

Run `python -m scripts.detection.report docs/detection/generated/live.json`. **Observed TTD** is the first collector alert availability minus AWS event time. **Observed log delay** is first collector observation minus AWS event time. Both include polling and any delay before collection began; they are measured observations, not service guarantees. A one-shot collection after the workflow cannot reconstruct earlier availability. Mock runs receive no live latency. A few comparisons cannot establish a production false-positive rate.

## Completion, boundaries and teardown

Detection completion requires N2 to remain expected, A2 to successfully obtain the exercise role and produce a retrievable independent alert, and missing/misleading context to remain visible. B2 is a distinct prevention result: denial of PR issuance while main works. The detector does not revoke credentials or stop a deployment. Nothing here establishes the later EKS, data-read or transfer steps.

After retaining sanitized evidence, remove or disable `DETECTION_DEMO_ROLE_ARN`, restore coordinated OIDC settings/trust/checker behavior, revoke the temporary detector GitHub credential, unset local token variables, and tear down the isolated exercise resources through the reviewed root procedure. Do not delete a shared GitHub OIDC provider. Confirm the normal release identity check works after restoration.

Sources: [GitHub OIDC](https://docs.github.com/en/actions/reference/security/oidc), [GitHub run attempts](https://docs.github.com/en/rest/actions/workflow-runs), [AWS STS logging](https://docs.aws.amazon.com/IAM/latest/UserGuide/cloudtrail-integration.html), [CloudTrail LookupEvents](https://docs.aws.amazon.com/awscloudtrail/latest/APIReference/API_LookupEvents.html), [EventBridge management events](https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-service-event-cloudtrail-management.html).
