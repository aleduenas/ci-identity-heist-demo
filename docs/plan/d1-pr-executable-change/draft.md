# D1 — Detect when a pull request changes code its automated checks execute

This option would alert when a new push changes a build/test script or another input that PR checks execute, giving security and engineering a chance to inspect the change before or during its execution.

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

## Where D1 acts and what it is trying to prove

D1 looks at the change that starts the CI compromise: the attacker edits a build/test script, pushes it to an existing PR, and lets automated checks run it before human review. It asks whether an independent detector can surface that modification and whether the resulting alert arrives before or after the changed script executes.

In normal development, an engineer pushes a change, gets automated feedback, and has a person review it before merging and trusted release. The attack exploits the gap between those stages: PR code runs before approval. If that job can obtain deployment permissions, the attacker may reach the backend without merging.

A **CI runner** is the machine executing the automated workflow. An **executable input** is code or configuration that causes that job to run behavior, such as its build/test entrypoint, a script that entrypoint calls, or a package lifecycle hook. A PR update, sometimes described as a synchronization event, tells the detector that another commit has arrived. The **diff** shows what changed; the review state indicates whether the proposed changes have been reviewed.

Tests and application code are also executable. A legitimate assertion change can run during testing, and a legitimate build-script change can resemble the simulated attack. D1 therefore creates a reason to investigate a risky change; it cannot determine malicious intent from a filename, an agent identity, or the fact that code executes.

## What the small detector would do

A separately controlled GitHub receiver or detection workflow would examine changed paths and actual diffs on unreviewed PR updates. Its scope would be the selected job's executable inputs, identified with engineering.

The proposed rule is: **surface a new push that modifies a configured CI-executable input before the change has been reviewed**, especially when the actor is the coding-agent identity. Include enough context to inspect the edit and find the corresponding run. It is an alert-first rule: it would not automatically stop the job or declare the account compromised.

The inputs and outputs would be explicit:

| Information | Why the detector needs it |
| --- | --- |
| Repository, PR and commit | Identify the precise proposed change rather than a later branch state |
| Push event time and actor | Establish when the action happened and which identity submitted it |
| Review state for the change being evaluated | Distinguish the unreviewed update from already reviewed work |
| Changed paths and actual diff | Explain which executable input changed and what behavior was edited |
| Selected job and its configured executable inputs | Connect the file change to code this CI job really runs |
| Workflow-run link; ticket reference if available | Give the investigator operational context without assuming a ticket proves safety |
| Independent detection record and alert time | Establish that security received a result outside the modified job |

An **independent detector** is controlled outside the PR branch the attacker can edit. The attacker must not be able to silence the check by modifying the same PR or replace its evidence with a reassuring message. The changed job's harmless execution marker can show that the test script ran; its own output does not establish that security received an alert.

**Illustrative alert, not an observed result:**

> An unreviewed update to this sandbox PR changed a script executed by its automated checks. The push used the coding-agent identity. Review the linked commit and diff, the configured script invocation, and the workflow run. This is a risky executable-input change requiring inspection; compromise has not been established.

The alert would carry the actual repository/PR/commit, actor, paths and run link. Missing review or execution context is a visibility gap, not evidence of safety.

## Planned validation: normal work and a harmless attack simulation

Use an owned sandbox, synthetic identities and harmless changes. Before either run, identify the job, executed script, executable-input scope and expected alert destination. Keep the detector in monitor-only mode.

**N1 — normal development comparison**

1. Open or use a ticket-linked sandbox PR and push a routine application change or ordinary test-assertion edit.
2. Record the push time, commit, actor, diff and review state. Let the normal checks execute and retain their run link.
3. Examine whether the edit matches the agreed executable-input scope. Do not exempt it merely because it is a test change.
4. Inspect the independent detector's result. If the routine change falls outside that scope, expect no executable-input escalation. If it is flagged, show that the alert can be correctly triaged as expected work and record the noise.

N1 passes when the classification follows the actual scope and diff, with normal feedback available. Ignoring all test-file edits would not establish useful coverage. A legitimate build-system edit would also help assess alert noise before considering a blocking follow-up.

**A1 — attacker behavior represented by a harmless marker**

1. Use the simulated coding-agent identity to push another update to an existing unreviewed sandbox PR.
2. Change the precise build/test script the chosen job executes, adding a harmless marker rather than malicious behavior.
3. Record the same event and change context as N1. Let the workflow run and confirm that the marker appears because the changed script was executed.
4. Retrieve the independent detection result and verify that it identifies this PR, commit, executable-input change and associated run. Record when the alert first becomes available to security.
5. Compare that alert time with both the push time and the changed script's execution time. Explain whether the signal arrived before execution or only afterward.

A1 passes the focused detection test only if the intended script executed and an independent alert or investigation result surfaced the risky modification. A raw push event alone is insufficient. A marker without an alert proves execution, while an alert without execution evidence does not establish the pre-review execution condition in this test.

Neither result establishes AWS access, EKS replacement or data transfer. If a safeguard stops the run, record that boundary; later actions remain unobserved.

## Evidence, timing and what a demo can establish

Retain sanitized events, diff, configured invocation, review context, run link, marker, independent detection and alert timestamp. Another person should be able to connect the result to its commit.

**D1 time to detect (TTD)** is the first independently available security-alert time minus the PR push-event time. **Log ingestion delay** is the first searchable-log time minus that same event time. Record event, searchable-log and alert times separately in UTC. Also report whether the alert preceded script execution; a short processing time by itself does not answer that question.

For each run, record expected/actual classification, legitimate alerts and investigation readiness. One pair is a focused check, not a production false-positive rate. All values remain unmeasured.

A later **runnable local demo** could process mock PR events, diffs and executable-input context to produce alerts. This demonstrates rule behavior on supplied inputs, not real GitHub delivery, available review metadata, script execution or security-side latency. A sandbox workflow provides those additional observations only where actually collected.

## Optional prevention: approval before the privileged job

After the monitor-only comparison, a separate experiment could require trusted approval before a privileged job runs when executable pipeline inputs change. Keep ordinary unprivileged PR feedback available where possible. This is a proposed gate around privileged execution, not a reason to stop every test job.

Push the harmless change without approval and verify that the privileged step does not execute. Retain approval context, independent security evidence and job outcomes. Confirm ordinary feedback and approved execution still work.

Prevention passes only if the privileged action did not take effect before approval. An alert after that job ran remains detection. If the gate stops the simulation, subsequent deployment or data-access phases are unobserved in that run. The concept does not assign this optional D1 experiment a separate B-number.

## Practical limits and decisions before building

D1 offers a familiar PR diff and visible script marker for a small demo. Its trade-off is noise: modifying CI-executed code is ordinary development, so scope and alert wording matter.

A dependency or executable input outside the configured scope may carry behavior the rule misses. Review metadata may not answer every question about a particular update. Letting the PR control the detector undermines the evidence. These limitations should guide the eventual build and normal-work comparison rather than being hidden by a favorable example.

Before selection, software/platform owners should agree the executable inputs, typical legitimate edits and privileged jobs. Security needs independent detection, evidence retention, alert routing and triage.

The documented repository separates PR checks from main-bound release roles and keeps untrusted PRs off the private runner. That design does not establish the concept's hypothesized PR-to-deployment path. No AWS apply or live EKS acceptance is recorded. This proposal does not require weakening those safeguards to demonstrate D1's focused behavior.

## Draft message for the engineering channel

> We are planning a sandbox check for a hypothetical route from stolen AI coding-agent credentials to customer data. An attacker could edit an existing PR's build/test script, have it run before human review, and, if that job can reach deployment permissions, replace an EKS backend that already has data access. We have not demonstrated that route at Relay.
>
> Proposed change: an independently controlled alert when an unreviewed PR update changes an input its automated checks execute. The alert would include the commit, diff and run so we can inspect the behavior. Legitimate tests and build scripts are executable too; a flagged edit is not automatically malicious. This first version would alert, while ordinary PR feedback continues.
>
> Software engineers: identify the scripts, hooks and other inputs our selected check executes, and provide a routine change plus a legitimate build-change example for comparison. Platform/CI owners: confirm when those inputs run, where privileged access begins, what review/run context is available, and where the detector can operate outside the editable branch. Security: name the alert owner and destination, agree triage expectations, and retain the evidence.
>
> Done for the focused check means a harmless script-marker push actually runs and produces an independent, actionable alert; normal work is either unflagged or correctly triaged; and we record push, execution and alert times. Alerting does not stop execution. A later, separately tested privileged-job approval gate would count as prevention only if that job cannot run before approval and normal unprivileged feedback remains usable.

## Source and related planning documents

The [immutable concept](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md), D1 in §6 and protocol in §§5/8, remains authoritative. The [assignment](../take_home.md) requires a future artifact and validation plan. This appendix sits outside the 2–3-page write-up.

See the [assignment guide](../assignment-draft/README.md), [submission draft](../submission-draft/draft.md), [repository architecture](../../architecture.md), and [implementation ledger](../../implementation-status.md). The concept's D3 recommendation and conditional D2 fallback remain unchanged; no final control is selected here.
