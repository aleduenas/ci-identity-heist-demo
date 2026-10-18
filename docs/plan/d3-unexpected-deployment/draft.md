# D3 — Detect backend changes that do not match a trusted release

An attacker uses valid deployment permissions to replace the backend application; D3 would alert when that accepted change does not match an independently recorded trusted release.

**Status:** Expanded planning draft, 2026-10-17. No detector has been built or tested; results and timings are unmeasured. D1–D4 remain options. This detailed explanation supports the eventual short assignment write-up.

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

## Where D3 acts and what it is trying to prove

D3 covers steps **18 and 21–23**: the attacker discovers deployment permission, prepares a replacement application, and uses that permission to change the running backend. It looks for **successful misuse of a permission**, rather than an action rejected for insufficient permission.

An **AWS role** is an identity with assigned permissions; workflows can receive temporary credentials for it. A **container image** packages application code and dependencies. A Kubernetes **Deployment** specifies how containers run, including their image. A **namespace** groups Kubernetes resources and scopes permissions here.

Changing a Deployment's image can therefore replace the application without granting the deployment identity direct database access. If the replacement starts with the original workload's runtime identity and connectivity, it may use the application's legitimate data access. D3 detects the workload change; it does not, by itself, prove database access or exfiltration.

The concept recommends D3 as the main demonstration because it compares legitimate and unauthorized changes under the **same role**. D2 remains its narrower fallback if independent release correlation is too cumbersome. Neither is finally selected here.

## What a normal release looks like

Normally, reviewers approve an engineer's PR and it reaches the protected main branch. A trusted workflow builds an image, publishes it to the registry—Amazon ECR here—and uses the deployment role to change the backend Deployment.

Kubernetes attempts a **rollout**: starting containers from the requested image and replacing the previous version. The workflow waits for completion. The attacker wants to misuse this normal image-change permission.

The normal release provides two different kinds of evidence:

- A trusted release record explains **why** a change was expected: which run, commit, target and release time.
- A Kubernetes audit event records **what API action happened**: which identity changed which resource, when, and whether the request succeeded.

An **audit event** records a Kubernetes API operation. EKS can send it to **CloudWatch**, AWS's log storage and search service. Event time differs from the time the delivered log first becomes searchable.

D3 would compare these records. This **correlation** decides whether the backend change belongs to the intended release, rather than merely occurring nearby.

## Proposed detector: inputs and decision

A future detection rule or small correlation component would compare successful backend Deployment changes with trusted release records and produce a retrievable alert explaining an unmatched change.

The inputs would be:

1. **Kubernetes audit evidence:** identity, successful `patch` or `update`, target Deployment, namespace, event time and decision.
2. **Independent release evidence:** trusted workflow run, commit, deployment target and release timing, plus the change context available from that source.
3. **Image-change evidence:** before/after Deployment snapshots or change history if the audit event does not contain sufficient image detail.

The release record and detector must sit outside the attacker's PR branch and workload. A compromised job printing “approved release,” a job-selected label, or a familiar role name does not prove authorization.

A match needs the **right target and relevant change context**, within a defined time window. Include the expected image where trusted evidence supplies it. An unrelated release during that window cannot authorize this mutation.

The draft decision cases are:

| Observed situation | What the detector should explain |
| --- | --- |
| Accepted target change with matching independent release evidence | Expected release; no unauthorized-deploy escalation. |
| Accepted target change with no matching release after the agreed correlation allowance | Unmatched-change alert with identity, target, timing and available image evidence. |
| Release feed is missing, late or incomplete | State the evidence gap explicitly; an unmatched-change alert must not claim the feed proves malicious origin. |
| Several releases overlap, or change context cannot identify the matching one | Show the ambiguity rather than treating any nearby release as authorization. |
| Mutation is denied | A blocked action; not the accepted-change behavior D3 is intended to demonstrate. |

Agree how to handle delayed records, concurrent releases, emergency changes and rollbacks before testing. Authorized rollbacks need recognizable trusted evidence too. Preserve ordinary release flow without requiring a reviewer to maintain an image allowlist.

## What an alert would mean

An **illustrative, unmeasured alert** could read:

> Backend Deployment changed without a matching trusted release. The Kubernetes API accepted a patch by the deployment role in the sandbox application namespace. Separate before/after evidence shows the image changed to harmless image B. No corresponding trusted release was found within the configured comparison window. Review the audit event, image snapshots and release-feed status before attributing intent. This alert does not establish database access or data transfer.

The alert should link the target, audit record, release comparison, image evidence and timestamps, explaining whether release evidence was available.

## N3: prove that a normal release remains normal

**N3 is the legitimate comparison run.** Its purpose is to show that ordinary releases do not produce the same unauthorized-change escalation.

1. Identify the sandbox backend Deployment and namespace, intended role, trusted release workflow and independent evidence source. Record the starting image.
2. Use the trusted release workflow to deploy a new harmless application version.
3. Collect its independent run, commit, target and time record.
4. Collect the accepted Kubernetes mutation and inspect the resulting Deployment and running image. If the audit event omits image detail, retain separate before/after snapshots.
5. Confirm the detector links this change to the correct release and does not escalate it as unauthorized.
6. Record delayed records, ambiguous matches or manual investigation required; do not quietly discard them from the result.

Require an explainable release match, not simply “no alert.” Record false escalations, their causes and operational effect.

## A3: prove that the same role's unauthorized change is noticed

**A3 is the simulated attacker run.** It uses a harmless replacement image and the concept's assumed sandbox PR context. It does not require malicious application behavior or real customer records.

1. Record the starting Deployment image and confirm the test identity is the **same deployment role used in N3**.
2. From the authorized sandbox simulation of the compromised PR context, attempt to replace the backend image with harmless image B, without a corresponding trusted release.
3. Establish that the Kubernetes API **accepted** the mutation. Retain the outcome and independent audit event.
4. Inspect the Deployment and running containers to establish the actual image change. Retain snapshots if the audit event lacks sufficient detail.
5. Confirm that the independent detector produces a retrievable unmatched-change alert. Inspect its release comparison and whether it reports missing evidence accurately.
6. Preserve sanitized evidence, then restore the legitimate mock image and record the rollback.

An accepted change with a failed image pull does not prove the replacement ran; report the failed rollout separately. A trust denial, private-endpoint connectivity failure or Kubernetes denial may block the attack, but does not pass this accepted-change detection test.

Check role permissions, private-cluster reachability, image availability and runtime assumptions in the selected sandbox without weakening existing safeguards to manufacture success.

## Evidence, pass/fail and timing

N3 passes its planned comparison when the trusted release changes the image and the detector explains the correct release match without unauthorized-deploy escalation. A3 passes its planned detection comparison when the same-role change is accepted, the running image changes, and the independent detector produces the expected alert.

A raw audit event or an alert without a demonstrated release comparison is insufficient. Missing release data is a limitation, not proof that no release happened.

For each run, retain the release record, mutation outcome, pre/post image evidence, audit event, correlation result and alert reference. Record three UTC times separately:

- **Event time:** when the accepted Deployment change occurred.
- **Log-available time:** when its audit record first became searchable.
- **Alert-available time:** when security could independently retrieve the detection result.

**Time to detect (TTD)** is alert-available time minus the accepted A3 change's event time. **Log ingestion delay** is log-available time minus event time. These distinguish slow audit delivery from additional detection delay.

Record N3 false escalations, A3 misses and investigation readiness. This small comparison cannot establish a production false-positive rate; timings require an actual test.

A separate preventive follow-up could gate deployments on trusted workflow context. That is not required for the D3 detection demonstration. If tested later, run it separately and confirm trusted delivery still works; do not claim later data-access or egress phases occurred during a run stopped at deployment.

## What a local demo can and cannot prove

A local demo could use sanitized mock audit and release records to show normal matching, an unmatched same-role change and an evidence gap. It would prove behavior on those records.

Actual audit fields, delivery, connectivity, permissions, image retrieval and independent release metadata require live evidence. The concept notes best-effort EKS audit delivery that typically takes minutes; do not promise real-time detection.

The current repository documents main-bound OIDC, separate build/deploy roles, a private trusted runner and a private EKS endpoint. Its design does not establish the hypothesized PR-to-deployment path. The handoff ledger also reports no AWS plan/apply, live EKS rollout or audit-delivery validation. Existing local/static checks do not fill those gaps.

Before choosing D3, establish whether independent release evidence can distinguish N3 from A3 despite delays and overlapping releases. Otherwise, retain the limitation and the concept's D2 fallback.

## Draft engineering-channel message if D3 is selected

> We are evaluating a scenario where stolen coding-agent GitHub access lets an attacker change a script PR tests run. If that job obtains deployment access, the attacker may replace the backend and inherit its data access. Merge review would occur after the first execution.
>
> The proposed check would alert when the backend's Kubernetes Deployment—the configuration selecting which application image runs—is successfully changed without a matching trusted release record. Normal releases and the attacker may use the same deployment role, so the role name alone cannot decide whether a change is expected.
>
> Application engineers: please identify the backend target and image-change flow, explain approved emergency releases and rollbacks, and help provide harmless versions for the normal and attacker comparisons.
>
> Platform engineers: please confirm audit visibility and image snapshots, identify independent release records with run, commit, target, time and available image context, and define delayed/concurrent-release handling without interrupting daily delivery.
>
> Security: please identify the alert destination and investigation owner, and agree what an analyst should see when a change is unmatched versus when release evidence is missing.
>
> Acceptance would compare a normal trusted release with an accepted same-role change lacking that release evidence: the first should match normally, the second should produce an independent alert with measured timing. We would keep the existing release process working and test any preventive gate separately. This remains a synthetic sandbox proposal; no vulnerability or detection result has been established.

## Source and related drafts

- [Immutable concept](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md), especially §§1, 4–9; D3 recommendation and D2 fallback remain unchanged.
- [Assignment instructions](../take_home.md).
- [Assignment map](../assignment-draft/README.md) and [short submission draft](../submission-draft/draft.md).
- [Repository architecture](../../architecture.md) and [implementation handoff](../../implementation-status.md), for the existing sandbox boundary and unverified live prerequisites.
