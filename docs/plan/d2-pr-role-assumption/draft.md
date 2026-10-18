# D2 — Detect when pull-request tests obtain AWS deployment access

An attacker steals an AI coding agent's GitHub credentials, changes code that automated PR tests execute, and uses that execution to try to obtain AWS deployment permissions. This option would alert at the point where the PR test job receives those permissions, before considering any later application replacement or data theft.

**Status:** Expanded planning draft, 2026-10-17. No detector has been built or tested; all results and timings are unmeasured. D1–D4 remain options. This detailed explanation supports the eventual short assignment write-up.

## The full attack, in plain English

A **pull request (PR)** proposes a code change for review. **Continuous integration (CI)** runs automated checks on that change, often before a person approves it. **Amazon EKS** runs the backend application in containers. The attacker tries to turn permission to propose code into permission to replace that running application.

The complete hypothetical sequence is below. Every action is explained here; the numbers also preserve the original concept's 26-step order.

1. An attacker runs a credential-stealing campaign through phishing, malicious websites, and compromised software.
2. The campaign obtains credentials belonging to a junior developer's AI coding agent.
3. The attacker discovers that those credentials can read private GitHub repositories, create branches, push code, and work with PRs.
4. The attacker impersonates the coding agent without needing to manipulate the developer directly.
5. The attacker examines the repositories available to that agent.
6. The attacker finds a backend application repository with active development.
7. The attacker sees that PRs are linked to development tickets and need human approval before merging.
8. The attacker also sees that updating an existing PR starts automated checks before that approval.
9. The attacker identifies an existing PR whose CI pipeline appears able to use the AWS role used for deployments.
10. The attacker modifies a build or test script in that PR to add malicious behavior.
11. The attacker pushes the change using the stolen agent credentials.
12. GitHub Actions automatically starts the CI workflow.
13. The workflow executes the changed script before a person reviews the new code.
14. The attacker's code is now running on the CI runner, the machine executing the workflow.
15. The attacker discovers that this PR job can obtain temporary AWS credentials for the deployment role.
16. The attacker investigates what those deployment credentials allow.
17. The attacker identifies the EKS cluster running the backend.
18. The attacker discovers that the deployment role can view and change the backend's Kubernetes Deployment, the configuration controlling its running containers.
19. The attacker also discovers that the deployment role cannot directly read the customer database.
20. The attacker reads the backend's source and configuration and learns that the application itself has legitimate customer-data access.
21. The attacker prepares a replacement application that keeps the normal functionality and adds unauthorized data access.
22. The attacker uses the deployment permissions to try to replace the legitimate container with that application.
23. If EKS accepts the change and can retrieve the replacement image, the new container starts with the application's normal runtime configuration.
24. The changed application uses its existing database access to retrieve customer financial records outside the intended business operations.
25. The attacker tries to send those records to an attacker-controlled HTTPS webhook, a web endpoint that receives data.
26. If outbound traffic is permitted, the records reach that endpoint and leave the environment.

The two important permission changes are **GitHub code-editing access becoming AWS deployment access**, then **deployment access becoming indirect customer-data access through the application**. The attacker does not start with a privileged employee's database credentials. Human merge review, SAML sign-in, IAM permissions, and Kubernetes permissions can all exist while the narrower hypothesized gap remains: unreviewed PR code can reach a deploy-capable job.

For an eventual test, the credentials, repository, application, customer records, and receiver would all be synthetic or owned sandbox resources. This is a hypothesis to validate, not a claim about Relay or a result from the existing repository.

## Where D2 acts and what it is trying to prove

D2 focuses on the action described in item 15 above: **an automated job testing an unreviewed PR obtains the AWS identity allowed to deploy the backend**. If the job has already been made to execute the attacker's script, the attacker can use permissions issued to that job. The proposed detector should recognize that the permissions were issued in the wrong workflow context.

The suspicious condition is not simply that temporary credentials exist; trusted release jobs need them too. Nor is it necessarily an AWS permission error. Under the attack assumption, AWS accepts the request because its configured trust is too broad. The question is whether security can notice a *successful* grant of deployment access to PR validation.

This detector would establish an unexpected role assumption. It would not, by itself, establish that the attacker changed EKS, read a database, or sent data outside the environment. Those later actions need their own evidence.

## What a normal workflow should look like

Two jobs have different purposes. A **PR-validation job** tests proposed code so that reviewers can decide whether it is safe to merge. A **release job** ships approved code to the running environment. The intended boundary is that testing proposed code should not, merely by running, gain the authority to replace the application.

An **AWS IAM role** is an AWS identity with defined permissions. The deployment role is the identity authorized to change the application. To **assume a role** means to obtain temporary credentials for that identity. Two configurations matter: the role's **trust policy** controls who can obtain those credentials; its permissions, together with Kubernetes authorization, determine what the holder can do afterward.

In the concept's OIDC-based sandbox, the normal release sequence would be:

1. A person reviews the change and it reaches the approved release path.
2. GitHub starts the intended release job. With the necessary OIDC permission configured, the job requests an identity token from GitHub. **OpenID Connect (OIDC)** is the identity mechanism used here; this token describes the workflow context rather than being a permanent AWS key.
3. The job asks **AWS Security Token Service (STS)** to exchange that identity for temporary deployment-role credentials. The relevant API operation is `AssumeRoleWithWebIdentity`.
4. AWS checks the configured trust and, if it accepts the request, issues temporary credentials. The release job then uses the role for the permitted deployment work.

The hypothesized failure is that a PR-validation job can complete that same exchange before its code has been approved. The credentials can be valid and the API call can succeed while the engineering boundary is wrong. This is why an alert limited to `AccessDenied` would miss the behavior being tested.

## What the proposed detector would read

The future artifact would be a small rule or script that combines AWS's record of credentials being issued with GitHub's record of the job that requested them. **Correlation** means establishing that those records describe the same activity, then evaluating whether that activity was expected.

| Information needed | Why it matters | Proposed source and constraint |
| --- | --- | --- |
| AWS account, deployment role, STS event time and request outcome | Establish which identity was requested and whether AWS issued credentials | AWS CloudTrail, the AWS API audit log; distinguish a successful assumption from a denied request |
| Identity-provider/token context recorded with the STS request | Help establish which GitHub context AWS accepted | Inspect the actual CloudTrail record, including a web-identity subject if present; do not assume it contains every GitHub token claim |
| Repository, workflow, triggering event, run ID and run time | Distinguish PR validation from an intended release and give engineers a run to inspect | GitHub run metadata collected independently of the PR's scripts; a job printing “release” is not an authoritative record |
| A demonstrated link between the AWS event and GitHub context | Avoid attaching an unrelated legitimate run to the suspicious credential issuance | Validate against the selected configuration; a similar timestamp or caller-chosen session name alone is insufficient |

The collector and detector would be controlled separately from the PR branch. Otherwise, the attacker could change both the code under test and the code deciding whether to alert. Retained evidence must also survive a compromised job changing its own logs.

### How the AWS-to-GitHub match must be established

The first implementation question is concrete: **which trustworthy field or combination of fields connects this STS request to this GitHub context?** We have not demonstrated that connection yet.

The AWS event may contain the web-identity token's subject, which can identify repository and workflow context. Whether it distinguishes a PR from a release depends on the actual subject configuration; jobs using GitHub environments can have a different subject structure. That subject must be inspected rather than guessed. A subject identifying a repository or context also does not automatically identify one exact workflow run.

The independent GitHub record supplies the run's event and workflow details. The eventual implementation must explain how those details are linked to the AWS event, and which conclusions the available evidence supports. A **role-session name** is a label supplied when requesting a role. Even if it resembles a GitHub run ID, it is a search hint unless its connection is independently established; attacker-controlled code could choose a misleading name.

If a reliable link cannot be established, the detector must return “context not verified” instead of inventing PR provenance. A mock event with an added `github_event` label can illustrate intended behavior, but cannot prove that real CloudTrail records contain that field or that the linkage works.

## How the detector would make its decision

1. Find an STS request for the selected backend deployment role.
2. Check whether it succeeded. A denial belongs in the test record as an existing boundary that stopped credential issuance; it is not the successful misuse D2 aims to detect.
3. Establish the requesting workflow context using the trusted evidence described above.
4. Apply the decision below and retain the evidence supporting it.

| Observed situation | Meaning | Proposed result |
| --- | --- | --- |
| Successful assumption linked to the intended trusted release job | The identity is being used for its documented purpose | Record expected activity; no PR-role-misuse escalation |
| Successful assumption linked to unreviewed PR validation | Proposed code obtained an identity that can change the running backend | Produce an actionable security alert |
| Successful assumption, but job context or linkage is missing/ambiguous | Security cannot reliably establish whether use was expected | Surface a visibility/correlation gap for investigation; do not silently classify it as trusted |

An alert should answer **what happened, why it matters, and where to look**. For example, the following is an invented illustration of the intended output, not an observed event or a raw AWS schema:

> **Deployment credentials issued to PR validation.** AWS issued the sandbox backend deployment role to a job independently identified as PR validation. That job is testing unreviewed code and should not need permission to replace the backend. Include the repository, PR/run link where verified, role, event UTC, and evidence establishing the match. CI/release owners should inspect the run; security should assess whether any deployment activity followed.

## How we would prove the detection works

The smallest demonstration would replay representative, sanitized AWS and GitHub records through the future detector. It should show the expected release, the suspicious PR assumption, and missing/ambiguous context. Any synthetic fields or unproven matching assumptions must be identified. Replay can prove the rule's decisions on those inputs; it cannot prove live AWS trust, real log delivery, or the full attack chain.

A later sandbox test would validate the identity boundary itself. It would use an owned repository and short-lived demo access, without stealing a real token, running an infostealer, or reading customer data. For D2, a harmless identity check is enough to establish which AWS role the job obtained.

### N2 — Normal release comparison

1. Record which workflow is intended to deploy the sandbox backend and which role it is allowed to use.
2. Have that trusted release workflow request the deployment role.
3. Use `GetCallerIdentity`, an AWS STS operation that reports the caller's AWS identity, to record which role was obtained. Retain the identity result, not the temporary secret credentials.
4. Obtain the STS audit event and independent GitHub run record; demonstrate their connection.
5. Run the detector. It should recognize expected release activity and make the supporting match inspectable.

**Pass condition:** The correct release context is established and the PR-role-misuse alert does not fire. Merely suppressing every event from a familiar role is not a pass.

### A2 — Simulated attacker comparison

1. In a separately scoped, intentionally permissive sandbox scenario, start a PR-validation job representing the compromised runner.
2. Let that job request the same deployment role and perform the same harmless identity check.
3. Confirm whether AWS actually issued credentials. If trust already denies the request, record the blocked boundary; the intended successful-assumption test has not occurred.
4. Obtain the successful STS event and independent PR-run context. Demonstrate why they belong together rather than relying on the job's own label.
5. Run the detector and retain its independent alert, supporting records, and availability time.

**Pass condition:** The PR job obtains the role in the detection-mode scenario, the detector correctly identifies the PR context, and a retrievable alert explains the unexpected grant. A raw STS record or a `GetCallerIdentity` response without an alert is insufficient.

Also test what happens when the run record is missing or a session label misleadingly resembles a release. The expected outcome is an explicit evidence gap, not an invented match. These check the detector's trust in its inputs; they are not additional attack paths.

### B2 — Optional prevention test, run separately

After detection evidence exists, a separate experiment would restrict the role's trust to the verified intended GitHub release context. Repeat the PR request and confirm that AWS denies it. Then repeat the trusted-release request and confirm that it still succeeds.

This tests a different result: **preventing the credentials from being issued**, rather than noticing them after issuance. The exact allowed subject/claims must be based on the actual repository and job configuration. Do not claim the remainder of the attack ran after this denial.

The existing Mybank design already documents main-bound OIDC trust and PR jobs kept off the private release runner. We would record those protections rather than weaken them to make the story work. Any permissive scenario remains separately scoped exercise configuration; no such configuration is created here.

## What we would measure and retain

Record all times in UTC and distinguish these three moments:

- **Action time:** AWS's event time for the successful role assumption.
- **Log-available time:** When the relevant audit record first becomes searchable.
- **Alert-available time:** When security can retrieve the detector's alert.

**Time to detect (TTD) = alert-available time − action time.** Log-ingestion delay is log-available time minus action time. If this is only a local replay, report replay processing time as such; do not present it as live CloudTrail-to-alert latency.

Retain the sanitized AWS event, independent GitHub record, explanation of the match, caller identity, detector decision, alert output, and the N2/A2/B2 result where tested. Record whether a release was incorrectly escalated and whether an engineer can identify the affected role and run. A few fixtures do not establish a production false-positive rate. All results remain **TBD**.

## Limitations and operational trade-offs

The hardest part is trustworthy context, not recognizing the role name. Missing records and ambiguous joins weaken what the detector can conclude. GitHub subject/environment choices can change available context. Log delivery delays affect when an alert can appear. Previously issued credentials may also be reused later; recognizing the original assumption does not establish every subsequent action.

D2 is a detection of a failed separation between testing and releasing. A successful alert does not revoke the credentials or stop a deployment by itself. The optional trust restriction is the prevention follow-up. Engineers should retain normal unprivileged PR checks and the intended release flow while that boundary is tested.

## Engineering-channel summary — ready to adapt if D2 is chosen

> **Risk we want to check:** Someone with a stolen coding-agent token could change a PR's build/test script. Automated tests run that script before review. If the test job can obtain the AWS deployment role—the identity allowed to replace our running backend—the attacker could deploy altered code and inherit the application's customer-data access. We have not demonstrated this in Relay's environment.
>
> **Proposed change:** Add an independent alert when PR validation successfully obtains the deployment role. Match AWS's credential-issuance record with trusted GitHub job information so the alert identifies the affected run and explains why the access is unexpected. Separately, test restricting that role to the intended release jobs so PR tests cannot obtain it.
>
> **Application/SWE owners:** Identify which build scripts, test entrypoints, and package hooks PR checks run. Confirm which checks actually need AWS access and whether any depend on deployment credentials. Help keep ordinary test feedback working without giving those tests deployment authority.
>
> **Platform/infra owners:** Review who the deployment role trusts and which GitHub job context AWS actually verifies. Provide the AWS audit records and an independent source of GitHub run details. Demonstrate how we can link them; a job's self-chosen session name is insufficient. For the separate prevention test, keep approved releases working while denying PR access to that role.
>
> **Security owner:** Maintain the rule outside PR-editable code, route alerts to a named responder, and include role, run, time, and matching evidence. Treat unverifiable context as an investigation gap rather than a clean result.
>
> **Done means:** The sandbox comparison recognizes a normal release, alerts on a successful PR-context assumption, and exposes missing context clearly. If prevention is tested, the PR request is denied while the release request still works. We will report actual evidence and timings; no production change or result is implied by this draft.

## Assignment fit and source references

The eventual deliverable is one small rule/script, its normal and suspicious comparison, a safe validation plan, and the engineering message above. The detector need not implement the later EKS or data-transfer stages to demonstrate this identity boundary. The [take-home instructions](../take_home.md) also require an AI usage note and a short final write-up.

The [original concept](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md), particularly its D2 hypothesis and validation protocol, remains unchanged. It recommends D3 as the main demo and D2 as a narrower fallback if D3's release correlation is too cumbersome; this explanatory rewrite makes no final selection. The second path remains deferred by the author.

See the [planning guide](../assignment-draft/README.md), [short write-up draft](../submission-draft/draft.md), [architecture](../../architecture.md), and [implementation ledger](../../implementation-status.md). The ledger records no live AWS provisioning, STS federation, or EKS acceptance for this exercise; local/static checks are not evidence that the attack or detection works.
