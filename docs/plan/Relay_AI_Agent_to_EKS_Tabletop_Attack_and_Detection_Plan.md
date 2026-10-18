# Relay Financial — AI Agent → CI/CD → EKS → Customer Data
## Purple-Team Tabletop: Attack Path, MITRE ATT&CK Mapping, and Four Testable Detection/Control Hypotheses

**Document status:** Proposed tabletop scenario and validation plan; **no Relay vulnerabilities, detection results, or timings have been verified**.  
**Date:** 2026-10-16  
**Environment given in the exercise:** AWS; EKS for container orchestration; engineers ship daily through GitHub → CI/CD → EKS; SAML single sign-on; a small number of employees have elevated customer-data access for support/debugging.  
**Sandbox implementation choices (not claims about Relay):** GitHub Actions, AWS OIDC, ECR, EKS, a sample backend application, a mock customer database, and a controlled HTTPS receiver.  
**Safety boundary:** All tests use a personal/authorized sandbox, invented customer records, and an owned data receiver. No production access or real customer-data transfer is required.

---

# 1. Complete attack path — plain English

**Objective:** Demonstrate how stolen credentials belonging to a junior developer's AI coding agent could ultimately give an attacker access to sensitive customer financial data.

**Environment:** Relay Financial — GitHub → CI/CD → AWS EKS, with SAML SSO and restricted customer-data access.

**Status:** Hypothetical attack path. We are making reasonable assumptions to test its viability, not claiming these vulnerabilities exist at Relay.

## Phase 1 — Steal the AI agent's credentials

1. I'm running an infostealer campaign using phishing, malicious websites, and compromised software.
2. One of my campaigns succeeds. I obtain credentials belonging to a junior developer's AI coding agent.
3. I investigate the credentials and discover they allow me to read private GitHub repositories, create branches, push code, and work with pull requests.
4. I use the stolen credentials to impersonate the coding agent. I don't need to compromise or manipulate the developer directly.

## Phase 2 — Find an opportunity in GitHub

5. I examine the repositories available to the coding agent.
6. I find a backend application repository where developers are actively working.
7. I discover that PRs are associated with legitimate development tickets and require human approval before merging.
8. However, pushing changes to an existing PR automatically triggers CI checks before the human review is completed.
9. I identify an existing PR where the CI pipeline appears to have access to an AWS role also used for deployments.

## Phase 3 — Compromise the CI runner

10. I modify a build or test script in the existing PR so that it contains malicious behavior.
11. I push the changes using the stolen coding agent credentials.
12. GitHub Actions automatically starts the CI workflow.
13. CI executes my modified script before a human has reviewed the new changes.
14. My code now executes inside the CI runner.
15. I discover that the PR job can obtain temporary AWS credentials associated with the deployment role.

**First major security boundary crossed:** I moved from a coding agent with limited GitHub access into CI, where I can obtain AWS deployment permissions.

## Phase 4 — Move from CI into EKS

16. I investigate what my AWS deployment credentials permit.
17. I identify the EKS cluster used by the backend application.
18. I determine that the deployment role can view and update the application's Kubernetes Deployment.
19. I also discover that this role cannot directly access the customer database.
20. I examine the backend application's source code and configuration. I learn that the application itself has legitimate access to customer records.

**Second major security boundary crossed:** I can modify a production application that already possesses the access needed to interact with customer data.

## Phase 5 — Access and extract customer data

21. I prepare a modified version of the backend application. It retains the original application's functionality but adds unauthorized data-access behavior.
22. I use the compromised deployment permissions to attempt to replace the legitimate container with my modified version.
23. Assuming the cluster accepts the deployment and can retrieve the modified image, my container starts with the application's normal runtime configuration.
24. The modified application uses its legitimate database connectivity to retrieve customer financial records beyond its intended business operations.
25. I attempt to transfer those records to an attacker-controlled HTTPS webhook.
26. If the environment permits that traffic, the customer data leaves Relay's infrastructure.

**Final outcome:** The attacker has potentially obtained customer financial data without directly stealing a privileged employee's credentials or obtaining database access from their original account.

### Attack chain at a glance

```text
Stolen AI agent credentials                  (initial foothold)
          |
          v
Existing GitHub PR modified                  (unreviewed code change)
          |
          v
Malicious script runs in CI                  (automatic PR validation)
          |
          v
AWS deployment role obtained                 (FIRST trust-boundary failure)
          |
          v
EKS backend Deployment modified
          |
          v
Customer-data access abused                  (SECOND trust-boundary failure)
          |
          v
Customer information exfiltrated             (attacker's intended outcome)
```

The key weakness being tested is that **code an attacker can submit using low-privilege development credentials may execute in an environment with substantially more privileged access, eventually allowing modification of applications that handle customer data.**

---

# 2. MITRE ATT&CK mapping — Enterprise Matrix order

The following follows the [MITRE ATT&CK Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/) from left to right, rather than the chronological sequence of the attack.

MITRE's current matrix separates **Stealth** and **Defense Impairment**, so both are shown.

| MITRE tactic | Relevant technique | Application to our attack |
|---|---|---|
| **1. Reconnaissance** | — | The attacker has a broad infostealer campaign, but we haven't specified any particular reconnaissance method before the credential theft. |
| **2. Resource Development** | [T1608.001 — Upload Malware](https://attack.mitre.org/techniques/T1608/001/) | Potentially relevant to staging the infostealer campaign. The exact delivery method remains unspecified. |
| **3. Initial Access** | [T1078.004 — Valid Accounts: Cloud Accounts](https://attack.mitre.org/techniques/T1078/004/) | The attacker uses the stolen agent credentials to gain access to private GitHub resources. |
| **4. Execution** | [T1059.004 — Unix Shell](https://attack.mitre.org/techniques/T1059/004/) | The attacker modifies a CI-executed build/test script, assuming a shell-based runner. |
| | [T1610 — Deploy Container](https://attack.mitre.org/techniques/T1610/) | The attacker deploys a modified backend container through EKS. |
| **5. Persistence** | — | No persistent access mechanism is deliberately established. |
| **6. Privilege Escalation** | [T1548.005 — Temporary Elevated Cloud Access](https://attack.mitre.org/techniques/T1548/005/) | The compromised PR job can obtain a more privileged AWS deployment role through an improperly scoped trust configuration. |
| **7. Stealth** | [T1078.004 — Valid Accounts: Cloud Accounts](https://attack.mitre.org/techniques/T1078/004/) | The attacker operates under a legitimate development identity, making GitHub activity appear to originate from an authorized agent. |
| **8. Defense Impairment** | — | The attacker does not explicitly disable logging, security tools, or other defenses. |
| **9. Credential Access** | [T1528 — Steal Application Access Token](https://attack.mitre.org/techniques/T1528/) | The initial infostealer obtains the coding agent's token. The compromised runner may also expose temporary AWS credentials. |
| **10. Discovery** | [T1526 — Cloud Service Discovery](https://attack.mitre.org/techniques/T1526/) | The attacker investigates AWS services available through the CI role. |
| | [T1613 — Container and Resource Discovery](https://attack.mitre.org/techniques/T1613/) | The attacker identifies Kubernetes namespaces, Deployments, and application workloads. |
| **11. Lateral Movement** | [T1550.001 — Use Alternate Authentication Material: Application Access Token](https://attack.mitre.org/techniques/T1550/001/) | Applicable if the attacker extracts and reuses the temporary deployment credentials to access EKS outside the original runner context. |
| **12. Collection** | [T1213.003 — Data from Information Repositories: Code Repositories](https://attack.mitre.org/techniques/T1213/003/) | The attacker examines private source code and deployment configurations to identify the path to customer records. |
| | [T1213.006 — Data from Information Repositories: Databases](https://attack.mitre.org/techniques/T1213/006/) | The modified application retrieves customer financial records using its legitimate database connectivity. |
| **13. Command and Control** | — | The scenario doesn't establish a persistent command-and-control channel. |
| **14. Exfiltration** | [T1567.004 — Exfiltration Over Web Service: Exfiltration Over Webhook](https://attack.mitre.org/techniques/T1567/004/) | The attacker attempts to send customer records to an external webhook. |
| **15. Impact** | — | The defined objective is data theft, not disruption, destruction, or manipulation of the organization's systems. |

The conditional mappings are intentional. For example, stealing a token does not automatically establish lateral movement, and having an infostealer campaign does not establish which reconnaissance technique was used.

**Mapping precision:** These are scenario-level mappings, not proof that every technique occurred. In particular, **T1548.005** is an analytical fit for temporary privilege gain only if PR-context use of the AWS role represents the inappropriate elevation described; ordinary, authorized role use by a trusted workflow is not by itself an attack. **T1550.001** is conditional on separate reuse of authentication material and should be omitted from observed results if the adversary never leaves the runner. We retain these qualifications instead of inventing additional actions.

---

# 3. Most relevant MITRE techniques for this case

For the actual purple-team demonstration, I would prioritize the techniques that best represent the transitions in our attack.

### T1078.004 — Valid Accounts: Cloud Accounts

Stolen agent credentials are used to make unauthorized GitHub changes under an authorized identity.

### T1059.004 — Unix Shell

Unreviewed PR changes cause malicious script execution inside CI.

### T1548.005 — Temporary Elevated Cloud Access

The compromised CI job obtains AWS deployment permissions beyond those available to the coding agent.

### T1610 — Deploy Container

The attacker uses those deployment permissions to replace a backend application workload.

### T1213.006 — Data from Information Repositories: Databases

The modified application uses its legitimate runtime access to collect customer records.

### T1567.004 — Exfiltration Over Webhook

The attacker attempts to transfer customer data out of the environment.

---

# 4. What must be validated

The attack depends on several assumptions that we should preserve explicitly in our case study:

1. The stolen agent credentials permit modification of the selected PR branch.
2. GitHub Actions executes the modified script before human review.
3. The PR validation job can assume the AWS deployment role.
4. That role can update the backend application's EKS Deployment.
5. The replacement container inherits access sufficient to retrieve customer records.
6. The application can make an outbound connection to the selected exfiltration destination.

These aren't six separate vulnerabilities we've established. They are the conditions necessary for this particular attack to complete.

**The next logical step is to choose one of these transitions as our primary detection point.** We can then demonstrate the entire chain using simulated data while concentrating the control and measurements on one specific attacker action, as the assignment requires.

---

# 5. Tabletop setup and hypothesis

## Purpose

We are testing whether the full attacker sequence is viable **under the stated attack assumptions**, and where new, targeted security detections or controls could identify or interrupt it. A tabletop is not evidence that Relay actually has these gaps; it produces questions, proposed instrumentation, and an explicit validation plan.

## Starting hypothesis (H0, as defined for this exercise)

> **H0 — Full-chain success without the four proposed additions:** If an attacker steals usable coding-agent credentials and follows steps 1–26, the attacker can modify an open PR, execute code during CI, obtain deployment-role access, alter the EKS workload, read customer records through that workload, and exfiltrate the results. Assume ordinary baseline engineering safeguards exist, but none of the four *targeted controls below* is present or effective.

This is an **exercise assumption, not a statistical finding**. In a strict hypothesis-testing sense, the term “null” is being used here as the starting scenario given by the exercise rather than an independently established probability of compromise.

**The exercise explicitly preserves standard security practices:** human PR review and ticket association, protected main branch, SAML SSO, AWS IAM and Kubernetes RBAC, ordinary audit logs where configured, and restricted direct database access. The hypothesized failure is narrower: **the PR-triggered execution environment inherits a deploy-capable trust path**, and the other later steps are provisionally possible. We do **not** assume nonexistent authentication or universal admin access.

## Tabletop roles

- **Red / attacker:** Narrates the 26 steps, provides the proposed actions and timestamps, and makes clear which outcomes are assumed versus observed.
- **Blue / detection:** Identifies log sources, validates whether events are visible, and records when an independent alert becomes available.
- **Engineering:** Confirms intended CI behavior, normal release sequence, and operational impact of new detections.
- **Facilitator / recorder:** Tracks assumptions, decision points, evidence, blockers, latency, and open questions without treating tabletop outcomes as actual test results.

## Exercise sequencing

1. **Baseline / permissive simulation:** Confirm legitimate workflow behavior and safely exercise the entire chain using synthetic artifacts and data. Run candidate detections in **monitor-only** mode so the simulated attack can progress for evidence collection.
2. **Detection tests:** For each control, compare a normal action to the specific attacker action, capture the security-side signal, and measure detection time.
3. **Blocking tests, if applicable:** Enable a proposed preventive action *one at a time* and rerun that local step. Do not claim later phases happened during a run already stopped earlier.
4. **Debrief:** Classify each assumption as confirmed in sandbox, blocked in sandbox, not tested, or unknown at Relay; identify which evidence would be needed in the actual environment.

## Tabletop decision points

| Point | Question for engineering/security | Initial tabletop answer | Evidence needed |
|---|---|---|---|
| PR execution (steps 10–14) | Can changes to build/test scripts on an existing unreviewed PR execute automatically? | **Assume yes** | Workflow trigger, PR event, job logs |
| AWS trust (step 15) | Can that PR job obtain the production-like deployment role? | **Assume yes** | OIDC trust conditions and CloudTrail STS event, or controlled role-assumption result |
| EKS authorization (steps 16–18, 22) | Can the obtained role patch the backend Deployment? | **Assume yes** | EKS access mapping/RBAC and Kubernetes audit event |
| Data path (steps 20, 23–24) | Does the workload have data connectivity, and can a replacement use it? | **Assume yes** | Mock app runtime configuration and mock database audit/fixture results |
| Exfil path (steps 25–26) | Can the workload communicate with an unapproved HTTPS receiver? | **Assume yes** | Network/egress evidence and controlled receiver confirmation |

---

# 6. Four detection/control hypotheses

These are **hypotheses to implement and test**, not controls we claim Relay currently lacks or currently has. They deliberately detect meaningful attacker behavior **even when the existing identity possesses the required permission**. They are distinct from merely advising “least-privilege IAM.”

## D1 — Alert on executable CI-script changes to an unreviewed, existing PR

**Where it acts:** Steps **10–13**, GitHub before or during PR-validation CI.  
**Type:** Detection first; optionally an early CI gating control for high-risk changed paths.  
**Question:** Can a stolen coding-agent identity quietly add code that PR CI will execute before a person notices?

**Attacker behavior:** An agent credential is used to push changes to a build/test entrypoint, workflow-adjacent script, package lifecycle hook, or other executable CI input on an existing PR.

**Legitimate look-alike:** Engineers routinely push commits to active ticket-linked PRs; occasionally they legitimately adjust tests or build scripts. The changed file is **a reason to inspect**, not automatic proof of compromise.

**Proposed signal and rule:** On a GitHub push / PR synchronization event, examine changed paths **and the actual diff**. Alert if a new push to an unreviewed PR modifies a file the configured CI job executes, especially when the actor is the coding-agent identity. Include repo, PR, ticket reference if available, commit, changed executable paths, actor, and workflow-run link. A simple initial implementation could use a GitHub webhook receiver or a separately controlled lightweight workflow that sends detection metadata; keep the detection authority outside the attacker-editable branch.

**Test:**

1. **Negative/control sample:** Push a normal application-source or ordinary test-assertion change to a ticket-linked PR; CI runs as usual.
2. **Positive/attack sample:** Push a harmless marker change to the precise sandbox script that CI is configured to execute; this stands in for the attacker's malicious modification.
3. Confirm CI actually executed the changed script and that the independent detection surfaced the risky modification.
4. Optional prevention experiment: require a trusted approval before the *privileged* job runs when executable pipeline inputs change. Keep ordinary unprivileged PR feedback available where possible.

**Expected validation evidence:** GitHub PR/push event time; actor; diff paths; workflow run link; harmless execution marker; detection event and alert time. Report **TTD = alert available time − push event time** and whether the alert preceded CI execution. The optional gating test passes only if the privileged step did **not** run before approval.

**Failure modes / friction:** False positives from legitimate build-system work; a payload could enter via a dependency or a file not listed in the rule; an attacker who can edit the detection workflow itself may tamper with evidence. Start in alert-only mode and measure typical alert volume before gating.

**ATT&CK connection:** T1078.004, T1059.004 (and the code-repository activity represented by T1213.003).

## D2 — Detect deployment-role assumption from PR-validation context

**Where it acts:** Step **15**, the agent/CI → AWS trust boundary.  
**Type:** Identity-context detection, with a possible targeted prevention follow-up.  
**Question:** Is a role intended for trusted deployment being assumed during a job triggered by unreviewed PR code?

**Attacker behavior:** The compromised PR validation runner obtains AWS credentials for the deployment role. The AWS API action may be technically authorized under the assumed gap; **authorization is not the detection criterion**.

**Legitimate look-alike:** A post-merge release workflow assumes the same role to deploy a normal backend release.

**Proposed signal and rule:** Observe CloudTrail STS role-assumption activity (for an OIDC-based workflow, often `AssumeRoleWithWebIdentity`), then correlate the role/session and event time with **independently sourced GitHub workflow-run metadata**. Alert when the deployment role is used by a PR-validation job instead of an expected trusted release job. Where a trusted correlation exists, record repository, workflow, event type (`pull_request` versus release/merge), role, AWS account, run ID, and time. **Do not presume CloudTrail alone exposes all of GitHub's original event or PR claims**; verify the actual available fields. A role-session naming convention may assist correlation but is not independently trustworthy if the job chooses the session name.

**Test:**

1. **Negative/control sample:** Run a normal, trusted release workflow that assumes the role. Confirm it is recognized as expected behavior.
2. **Positive/attack sample:** From the intentionally permissive sandbox PR-validation job, perform a harmless role-assumption test and identity check (`GetCallerIdentity`) with mock resources only.
3. Verify CloudTrail records the STS activity and the detector correctly links it to the PR run without relying solely on attacker-controlled labels.
4. Optional prevention experiment: restrict trust by verified GitHub OIDC claims so the PR run cannot assume the deployment role; rerun only this step and record denial. This would *invalidate H0 at this boundary* if effective.

**Expected validation evidence:** GitHub run event/type and timestamp, successful or rejected STS event, returned AWS role identity if successful, correlation record, alert timestamp, and any trust-policy test result. Report TTD from role assumption to independent alert.

**Failure modes / friction:** CloudTrail ingestion delay; ambiguous run-to-session mapping; claims/session context may differ depending on GitHub environments; an attacker might reuse previously issued credentials. The control must prove its correlation works for the selected configuration, not infer provenance from a name alone.

**ATT&CK connection:** T1548.005; T1528 for credential/token acquisition context; T1078.004.

## D3 — Detect backend EKS Deployment modifications that lack a matching trusted release

**Where it acts:** Steps **18 and 21–23**, AWS/EKS deployment boundary.  
**Type:** Behavior-based detection (recommended **primary build** for a focused purple-team demo).  
**Question:** Can the same deployment role make an unauthorized production-like workload change, and will security notice that change independently of CI?

**Attacker behavior:** Using a role that **really can update** the target namespace, the attacker changes the backend Deployment to a replacement image. This is an allowed Kubernetes API action under H0, so an IAM `AccessDenied` alert will not help.

**Legitimate look-alike:** The release workflow routinely updates the same Deployment using the same role during normal releases.

**Proposed signal and rule:** Enable EKS **Kubernetes audit logs** to CloudWatch and detect successful `patch`/`update` operations on the targeted backend Deployment. Correlate each event with an independently recorded **trusted release event** (e.g., a post-merge deploy workflow's run, commit, deployment target, and time window). Escalate when the workload changed but there is no corresponding authorized release event. Record old/new image references using a separate before/after Deployment snapshot or change history **if the audit event doesn't contain sufficient detail**. This is **not** a manually maintained list of approved image versions, nor a policy that a reviewer must update for every release.

**Test:**

1. **Negative/control sample:** Let the trusted release workflow deploy a new harmless app version to the sandbox namespace; collect audit event and release context. It should not produce an unauthorized-deploy alert.
2. **Positive/attack sample:** Using the **same AWS deployment role** from the sandbox PR context, update the Deployment to harmless image B **without** a matching trusted release event.
3. Confirm the API request was **accepted** (for the detection-mode test), the running image changed, and the security-side detector alerted.
4. For a preventive follow-up, one could gate deployments on a trusted workflow context, but that is **not required for this detection PoC**. Roll back to the legitimate mock image after collecting evidence.

**Expected validation evidence:** Release-run record; `kubectl` outcome; pre/post Deployment image; Kubernetes audit record showing identity, verb, resource, namespace, time and decision; matched/unmatched release correlation; alert timestamp. Report TTD from **accepted malicious Deployment update** to security alert. Also report what the detector does if no release event is available.

**Failure modes / friction:** Audit records may not identify the originating GitHub PR; the Kubernetes identity can be identical for good/bad deployments; correlation needs independent release metadata, well-defined time windows, and a way to handle rollbacks/emergency changes. AWS EKS audit log delivery is best-effort and typically takes minutes, so avoid promising real-time detection.

**ATT&CK connection:** T1610 and T1548.005.

## D4 — Detect or block outbound transfer to an unapproved webhook from the backend workload

**Where it acts:** Steps **24–26**, attempted data exfiltration.  
**Type:** Egress behavioral detection; optionally egress allowlisting as prevention.  
**Question:** If the attacker gets past GitHub, CI, and EKS, can the modified application send customer-like data to an unexpected Internet receiver?

**Attacker behavior:** The replacement backend obtains synthetic customer records and issues an outbound HTTPS request to a controlled receiver that isn't part of its normal integration set.

**Legitimate look-alike:** The backend legitimately connects to its database and approved external APIs. HTTPS traffic itself is not malicious.

**Proposed signal and rule:** Observe the backend workload's outbound destination using **a real egress observation point** (for example a sandbox egress proxy with connection logs, or an explicitly supported network telemetry stack). Alert on traffic from the application workload to an unapproved destination, optionally correlating destination and timing with suspicious Deployment activity. For a blocking variant, restrict the app's outbound destinations to known required services. **VPC Flow Logs alone generally do not reveal HTTPS webhook URL paths or request bodies**, and may not reliably attribute flows to a pod without additional context; do not claim the logs show exfiltrated records unless the receiver or other trusted instrumentation confirms it.

**Test:**

1. **Negative/control sample:** Perform ordinary API operations that query the mock database and use only approved network destinations.
2. **Positive/attack sample:** Run harmless image B; have it read **invented customer records** and send an identifiable synthetic payload to **our own controlled HTTPS receiver**.
3. Confirm the receiver observed the payload and that the independent network telemetry generated the expected destination alert. Distinguish **exfil attempt detected** from **data successfully transferred**.
4. Optional prevention experiment: activate a supported egress restriction, repeat the test, and verify that the mock receiver gets **no payload** while normal integrations still work.

**Expected validation evidence:** Mock database access record (if enabled); network/proxy event with pod/workload-to-destination attribution; receiver receipt time/payload marker; alert time; allow/deny outcome. Report TTD from the **first malicious outbound attempt** to alert and, if prevention is enabled, whether the controlled receiver ever received the payload.

**Failure modes / friction:** Many normal APIs use changing external domains; proxy visibility requires routing traffic through it; encrypted traffic limits content inspection; DNS/IP churn and shared gateways complicate attribution; egress restrictions can break legitimate integrations. This is the last line of detection—not proof earlier steps were prevented.

**ATT&CK connection:** T1213.006 and T1567.004.

---

# 7. How the four proposed controls cover the chain

| Control | Primary steps | Security question | Legitimate comparison | Attack result targeted | Main evidence |
|---|---|---|---|---|---|
| **D1 — PR executable-change alert** | 10–13 | Did attacker-supplied CI-executable code enter an unreviewed PR? | Regular ticket-linked PR update | Alert / optional privileged-job gate | GitHub events, diff, run metadata |
| **D2 — PR-context role-assumption alert** | 15 | Is a deployment AWS role used by PR validation? | Trusted post-merge release role assumption | Alert / optional targeted trust deny | CloudTrail STS + independent GitHub run record |
| **D3 — Unexpected EKS deployment alert** | 18, 21–23 | Did backend workload change without an authorized release? | Normal release changes same Deployment | Alert on successful misuse of valid permissions | EKS audit + separate release evidence |
| **D4 — Unapproved egress alert** | 24–26 | Did backend send data toward unexpected Internet destination? | Normal app calls to approved services | Alert / optional block | Trusted egress telemetry + controlled receiver |

**Layering matters:** If D1 misses a modified dependency, D2 might still see inappropriate AWS role use. If the role use looks normal, D3 can still notice a release-inconsistent Deployment update. If the attacker deploys a workload in a way D3 misses, D4 can still surface outbound data transfer. The controls are **not** guarantees of detecting every variant; each has stated blind spots.

## Which one to implement as the single main demo?

**Recommendation: D3 — unexpected EKS Deployment change**, because it directly catches an attacker abusing a deployment permission the CI identity legitimately has; it is not simply a demonstration of insufficient IAM rights. It gives a clear normal-versus-malicious comparison under the same identity, and has an AWS-side audit artifact for independent timing. **But** D3 is only credible if the sandbox successfully correlates audit events to independent release evidence; the rule must not label *every* deployment as malicious or trust attacker-editable run labels. If that correlation proves too cumbersome, **D2** is a narrower fallback with a clear testable boundary.

For the complete tabletop, we retain all four as hypotheses; implementing all four is not required to demonstrate one well-chosen control.

---

# 8. Test protocol, validation criteria, and measurements

## Before running

- Scope to a private sandbox repo, an isolated EKS namespace/cluster, short-lived demo roles, ECR (if chosen), invented database rows, and an owned HTTPS endpoint.
- Record normal release behavior and the exact scope of GitHub token, AWS IAM role, Kubernetes RBAC, and workload runtime connectivity. Distinguish confirmed configuration from exercise assumptions.
- Put audit/detection collection **outside** the attacker-controlled PR branch and workload.
- Synchronize or accurately record UTC times from GitHub, AWS, Kubernetes, the detection service, and the test receiver. Note that event timestamps and log-ingestion times are different.
- Enable only needed log sources and use short retention and cost controls in the personal AWS account.

## Common test labels

- **N1–N4:** Legitimate comparison runs for controls D1–D4.
- **A1–A4:** Corresponding simulated attacker runs with the relevant action present.
- **B2 / B4:** Optional blocking tests for D2 / D4, run separately after full-chain monitoring evidence is captured.
- **P:** Positive = relevant attack behavior present; **N:** Negative = matching legitimate behavior. Both must be evaluated.

## Evidence ledger (complete once tests exist)

| Test ID | Control | Event UTC | Log available UTC | Security alert UTC | Detected? | Blocked? | False positive? | Evidence reference |
|---|---|---|---|---|---|---|---|---|
| N1 / A1 | D1 | TBD | TBD | TBD | TBD | N/A | TBD | TBD |
| N2 / A2 | D2 | TBD | TBD | TBD | TBD | Optional | TBD | TBD |
| N3 / A3 | D3 | TBD | TBD | TBD | TBD | N/A | TBD | TBD |
| N4 / A4 | D4 | TBD | TBD | TBD | TBD | Optional | TBD | TBD |

**Measurement definitions:**

- **Time to detect (TTD)** = first independently visible security alert timestamp minus attacker-action timestamp. Report measured values, not vendor promises.
- **Log ingestion delay** = first searchable log timestamp minus attacker-action timestamp.
- **Investigation readiness** = whether an analyst has enough evidence to identify the actor/session, target, suspicious behavior, and relevant run/change without depending on attacker-controlled logs.
- **True-positive test** = the simulation generates the intended signal; **negative test** = representative legitimate behavior avoids the same escalation (or is appropriately triaged as expected).
- **Prevention success (where tested)** = the forbidden action has **not** taken effect and the independent security event is still available.

**Pass/fail discipline:** Do not mark a test "pass" merely because an event exists in raw logs; the defined detection must produce a retrievable alert or investigation result. Do not claim data loss prevention on D4 if the webhook received the synthetic payload before an alert fired.

## Decision framework

1. **Attack step blocked by an existing standard control:** Record the real boundary as a finding; H0 fails at that step under that configuration. Do not force the test by bypassing actual controls in production.
2. **Attack action succeeds but detection fires:** H0's **access-path success** may still hold, but the added detection satisfies the "would we catch it and how quickly?" requirement for that behavior.
3. **Attack action succeeds and no signal appears:** Detection coverage gap; record missing telemetry, identity context, rule logic, or routing.
4. **Simulation cannot be executed safely or lacks evidence:** Mark **not validated**; retain it as a tabletop assumption.

---

# 9. Engineering-team handoff (draft)

**Scenario:** We are evaluating whether stolen credentials for a junior engineer's coding agent could be used to modify a ticket-linked PR, execute altered build/test code during PR CI, gain the AWS role used for deployment, update a backend application in EKS, and exploit the application's existing customer-data access. Every step is an exercise assumption pending validation; we are **not** claiming these conditions exist at Relay.

**Why PR review alone is insufficient for this test:** The attacker does not need the malicious PR merged to obtain CI execution; the CI validation job runs before human approval. If that job can obtain a deploy-capable AWS role, the post-review deployment boundary may already have been crossed.

**Four candidate checks:** (1) flag changes to code that CI executes on an unreviewed PR, (2) alert on deployment-role use from PR validation, (3) alert on EKS backend Deployment changes not associated with a trusted release, and (4) detect/block backend egress to unexpected webhook destinations. Each check has a normal comparison, a simulated attacker action, an expected independent signal, and a time-to-detect measurement.

**Minimum questions for engineering:**

1. Which PR workflow jobs run scripts or dependencies directly from the PR branch?
2. Which AWS roles can PR-validation jobs actually assume, and how are their GitHub OIDC claims restricted?
3. What Kubernetes resources can the deployment role mutate, and what run/release metadata exists independently of PR-editable files?
4. How is the backend granted customer-data connectivity at runtime, and what outbound Internet traffic is intentionally required?
5. Who receives and triages alerts for suspicious CI activity, AWS role use, Kubernetes changes, and abnormal egress?

**Expected output after testing:** A one-page result summary with confirmed/failed assumptions, the exact simulated action, screenshots/log excerpts or archived sanitized events, observed TTD, false-positive notes, operating impact, and recommended owner. Until that work is completed, **all control outcomes and latency values are TBD**.

---

# 10. References

The MITRE technique links appear in §2. Technical references for validating telemetry and the control hypotheses:

- [MITRE ATT&CK — Enterprise Matrix](https://attack.mitre.org/matrices/enterprise/)
- [MITRE ATT&CK — Temporary Elevated Cloud Access (T1548.005)](https://attack.mitre.org/techniques/T1548/005/)
- [MITRE ATT&CK — Deploy Container (T1610)](https://attack.mitre.org/techniques/T1610/)
- [MITRE ATT&CK — Databases (T1213.006)](https://attack.mitre.org/techniques/T1213/006/)
- [MITRE ATT&CK — Exfiltration Over Webhook (T1567.004)](https://attack.mitre.org/techniques/T1567/004/)
- [AWS — Amazon EKS control-plane audit logs to CloudWatch](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html)
- [AWS — CloudTrail user identity and STS source identity](https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-user-identity.html)
- [MITRE — Detection Strategy for Temporary Elevated Cloud Access (DET0393)](https://attack.mitre.org/detectionstrategies/DET0393/)
- [MITRE — Detection Strategy for Exfiltration Over Webhook (DET0153)](https://attack.mitre.org/detectionstrategies/DET0153/)

**Scope reminder:** This is an authorized tabletop and synthetic-data validation plan; it does not assert the attack works at Relay, and it does not include any real credentials, sensitive customer records, or attacker destination.
