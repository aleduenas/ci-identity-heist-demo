# Operation Leaky Pipeline: assignment mapping and draft guide

**Status:** Document-only working draft, expanded for clarity on 2026-10-17. No control has been selected or built in this drafting task; no attack, alert, prevention outcome, or detection time has been validated. The second attack path is deliberately deferred at the author's direction. This pack is not yet the completed take-home submission.

## Authority and reading order

The [original concept](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md) is the immutable authority for the attack narrative, assumptions, hypotheses, and qualifications. The [take-home instructions](../take_home.md) define the assignment requirements. This pack maps the former to the latter; it does not revise the concept or add another attack narrative.

**Start with whichever option you want to understand.** Every option draft now begins with the full 26-step attack in plain English. It then explains normal engineering behavior, the exact action being detected, technical terms and evidence sources, the proposed decision, and how a safe test would establish success or failure. You do not need to read the original concept or follow a numbered reference to understand the proposal. Source links remain for checking fidelity.

The assignment specifies AWS, EKS, daily GitHub-to-CI/CD delivery, SAML SSO, and limited elevated employee data access. GitHub Actions, OIDC, ECR, a mock backend/database, and an owned HTTPS receiver are the concept's sandbox choices, not additional facts about Relay. The attack does not depend on stealing an elevated support employee's credentials or bypassing SAML.

| Document | Purpose |
| --- | --- |
| [Write-up working draft](../submission-draft/draft.md) | Complete attack explanation, open choices, validation, AI note, and common engineering handoff |
| [D1: notice risky changes before PR checks run them](../d1-pr-executable-change/draft.md) | Explain which scripts automated checks execute; alert on unreviewed changes to those inputs; optionally gate privileged execution |
| [D2: notice PR tests obtaining deployment access](../d2-pr-role-assumption/draft.md) | Explain how a job receives AWS credentials; distinguish a trusted release from PR validation; optionally deny PR access to the role |
| [D3: notice a backend change outside a trusted release](../d3-unexpected-deployment/draft.md) | Explain container replacement and compare the accepted change with independent release evidence, even under the same role |
| [D4: notice the backend contacting an unexpected destination](../d4-unapproved-egress/draft.md) | Explain network visibility, identify the originating application, and separate an alert from receipt or blocking of synthetic data |

Each new file has its own folder under `docs/plan`. These are expanded planning explanations, not a claim that the entire pack fits the assignment's 2–3 pages. Once a control is selected, condense that option into the final short write-up and retain the detailed version as supporting material. Actual page count must be checked after formatting. No slide deck or executable artifact is being produced now.

The engineering-channel message at the end of each option is self-contained: it explains the risk, the proposed change, what application engineers should do, what platform engineers should do, who handles alerts, and what evidence would mean the test is complete. Monitoring and optional blocking are described separately so the requested engineering work is clear.

## Requirement-by-requirement mapping

| Assignment requirement | Source and draft treatment | Current status |
| --- | --- | --- |
| Describe two realistic attack paths to customer/financial data | Concept §1 supplies one complete 26-step path, reproduced in plain English at the start of each draft | One drafted; second deferred by author. D1–D4 are defenses on that path, not additional paths |
| Pick one path and explain why | Use the coding-agent → PR tests → AWS deployment access → application replacement → data chain; drafts explain why merge review happens too late for the initial CI execution | Primary path retained; second-path comparison deferred |
| State assumed attacker profile | Attack openings explain credential theft and impersonation before any AWS access is obtained | Drafted as an external credential thief impersonating an agent, without initial AWS/data privileges |
| Build one small working control/detection | Concept §§6–7; four separate option documents describe future artifacts | Intentionally unbuilt. No final D1–D4 selection |
| Explain why that control was chosen | Concept §7 recommends D3, with D2 as conditional fallback | Recommendation preserved; final rationale must match the eventual choice |
| Safe validation plan and measurements | Each option describes a normal run, harmless simulated attacker action, pass/fail evidence, timing, and any separate blocking experiment | Planned only; all outcomes and timings TBD |
| Short actionable engineering summary | Each option ends with a standalone channel message containing the risk, change, SWE/platform/security responsibilities, and completion criteria | Ready to adapt when one option is selected; no deployed fix claimed |
| Presentation: paths, selection rationale, attacker, validation, next steps | Concept §§1, 4–8; walkthrough outline below | Talking points drafted; second path, final selection, artifact, and results deferred |
| Present the script/rule/policy/check; optional mock-data demo | Future artifact described in each option document | No artifact or demo yet. Assignment permits SIEM pseudo-config; that is not claimed delivered here |
| AI usage note: requests, errors/untrusted output, personal checks | Working write-up records actual drafting use and the author's feedback about unexplained references and vague handoff text | Readability correction documented; earlier research history and personal technical verification must still be recorded truthfully |
| Short write-up of 2–3 pages plus built material | Select and condense one option from the expanded working drafts; keep detailed explanations as supporting material | Final length/export and built material pending; the full planning pack is not the short submission |
| Presentation with questions during an approximately one-hour interview | Walkthrough outline below | Leave room for discussion; the assignment does not require a one-hour prepared talk |
| No real Relay interaction or real customer/employee data; explicit assumptions | Each draft explains synthetic/owned test resources and distinguishes the hypothesis from observed results | Preserved throughout |

## Attack and assumptions to preserve

The concept's chain remains: stolen AI-agent credentials → existing ticket-linked PR modified → altered build/test script runs before review → PR job obtains the AWS deployment role → backend Deployment replaced → application runtime data access abused → attempted transfer to a webhook. The deploy role lacks direct database access; replacing data-capable code is the second trust boundary.

The concept §4 lists these six prerequisites verbatim:

> 1. The stolen agent credentials permit modification of the selected PR branch.
> 2. GitHub Actions executes the modified script before human review.
> 3. The PR validation job can assume the AWS deployment role.
> 4. That role can update the backend application's EKS Deployment.
> 5. The replacement container inherits access sufficient to retrieve customer records.
> 6. The application can make an outbound connection to the selected exfiltration destination.

These are conditions to test, not six established vulnerabilities. Image availability and private-cluster reachability also need to be established for a future sandbox demonstration; IAM permission alone does not establish either. Those are implementation prerequisites, not a replacement attack narrative.

Concept §5's H0 is an exercise assumption about full-chain success without the four targeted additions. Preserve human review, tickets, protected main, SAML, IAM/RBAC, ordinary audit logging where configured, and restricted direct data access. An observed standard control stopping the attack would invalidate that step's assumed success in that configuration. It would not justify quietly removing the control or claiming the later steps ran.

The ATT&CK mapping remains in concept §§2–3, including its conditional treatment of T1548.005 and T1550.001. It is supporting analysis, not an assignment requirement or proof that a technique occurred. This drafting task does not independently re-research the concept's external references.

## Keep all four hypotheses available

| Option | Boundary and future artifact | Minimum credible comparison | Main dependency or limitation |
| --- | --- | --- | --- |
| D1 | Attacker edits a PR script and automated checks execute it; independently inspect the changed code and alert on scoped executable-input changes | N1 ordinary app/assertion change; A1 harmless marker in a script CI actually executes | Maintain accurate executable-input scope; legitimate build changes can alert; keep detector authority outside the PR branch |
| D2 | PR checks obtain the AWS deployment role; compare AWS credential-issuance evidence with independent GitHub job context | N2 trusted release assumption; A2 PR-validation assumption of the deployment role | Independently establish run provenance; session naming or presumed CloudTrail PR fields are insufficient |
| D3 | Attacker replaces the backend under valid deployment permissions; compare the accepted Kubernetes change with trusted release records | N3 trusted deployment; A3 accepted same-role image update without matching trusted release | Independent release evidence, useful audit fields, correlation timing, and missing-feed handling must work |
| D4 | Changed backend sends records toward an unexpected receiver; observe its outbound destination and optionally restrict that traffic | N4 required integrations; A4 synthetic transfer to an owned receiver | Actual workload-attributed egress visibility; HTTPS receipt and blocking require separate proof |

The concept §7's recommendation is retained verbatim:

> **Recommendation: D3 — unexpected EKS Deployment change**, because it directly catches an attacker abusing a deployment permission the CI identity legitimately has; it is not simply a demonstration of insufficient IAM rights.

That recommendation is conditional on credible audit-to-independent-release correlation. The concept retains D2 as a narrower fallback if that dependency is too cumbersome. D1 and D4 remain available; no option is selected by this pack. A future selection should weigh the stated evidence dependencies, legitimate-traffic friction, and ability to demonstrate one small working artifact. Implementing all four is not required.

## Shared future validation and evidence contract

1. Scope any eventual work to an authorized private sandbox, synthetic identities/records, short-lived demo access, and an owned receiver. No Relay systems, domains, or employees are to be contacted.
2. Record actual token scope, workflow behavior, role trust, RBAC, runtime data access, image retrieval, and network reachability before attributing success to the chain. Keep detection authority and evidence collection outside the editable PR and modified workload.
3. Begin with a legitimate comparison. In a future permissive simulation, monitor-only detections allow full-chain evidence collection. A focused mock-event replay can demonstrate rule behavior, but cannot establish live AWS/EKS attack viability or delivery latency.
4. Run only the selected option's N/A pair for the small primary artifact. The other option tests remain planned alternatives. If full-chain testing is later undertaken, record each boundary separately.
5. Run optional prevention separately, one boundary at a time. Use B2/B4 for the concept's optional blocking tests; D1 also permits a separate privileged-job gating experiment. Record the stopping point and leave downstream phases unobserved for that run.
6. Preserve sanitized source events, independent correlation context, alert/investigation output, relevant before/after state, and rollback/cleanup evidence. Do not commit tokens, assertions, real records, Terraform state, or temporary credentials.

| Pair | Action time used for TTD | Comparison and evidence focus | Outcome |
| --- | --- | --- | --- |
| N1 / A1 | PR push event | CI-executable diff, actual marker execution, independent alert, whether alert preceded execution | TBD |
| N2 / A2 | Role assumption | Trusted GitHub run context + STS event + linked role identity + independent alert | TBD |
| N3 / A3 | Accepted Deployment update | Same deployment role, API acceptance, changed image, independent release match/mismatch, audit and alert | TBD |
| N4 / A4 | First simulated malicious outbound attempt | Workload/destination attribution, alert, receiver receipt or its absence in a separate block test | TBD |

Record event UTC, first searchable-log UTC, and first independently visible alert UTC separately. **TTD = alert time − relevant attacker-action time**; **ingestion delay = first searchable-log time − action time**. Mock replay processing time must be labeled as such. For each sample, record detected/blocked status, legitimate alerts, investigation readiness, and evidence reference. One positive/negative pair does not establish a production detection rate.

A raw event alone is insufficient for a passing detection: require a retrievable independent alert or investigation result and a legitimate comparison that avoids escalation or is correctly triaged. Successful transfer followed by an alert is detection, not prevention. Missing data is an explicit visibility/correlation gap, not proof of an authorized action or a successful test. Concept §8's evidence ledger remains an unfilled template.

## Relationship to the existing repository

The [architecture](../../architecture.md), [delivery guide](../../delivery.md), and [implementation ledger](../../implementation-status.md) describe a Mybank synthetic lab. They supply implementation context only; they do not override the concept or establish Relay's configuration.

The documented delivery design binds OIDC trust to `main`, separates build and deploy roles, keeps PR jobs off the private runner, and uses a private EKS endpoint. It does not establish the concept's assumed PR-to-deployment-role-to-cluster path. Workload identity and Deployment-update permissions illustrate the intended application-data boundary, but their live behavior is not proven. Document any future mismatch as an assumption or a blocked boundary; retain the current safeguards while planning a separately scoped simulation.

The delivery guide also describes broad TCP/443 egress; that is not destination allowlisting. Network-policy manifests do not establish live enforcement or D4 telemetry. The implementation ledger records **no AWS plan/apply, STS federation, live IAM/CNI enforcement, CloudTrail delivery, or EKS rollout**. Existing local/static checks must not be presented as attack/control validation. This task changes documentation only and does not advance those implementation statuses.

## Suggested presentation walkthrough

This is a discussion outline, not a slide deck or a fixed interview schedule.

1. **Problem and attacker:** Explain the assignment environment, the external credential thief, and the limited initial agent permissions. State assumptions and simulation boundaries.
2. **Attack path:** Walk through the immutable chain and its two trust boundaries. Say the second required path is deferred in this working draft; do not substitute a control or a later phase for it.
3. **Choice:** Show D1–D4 briefly, retain the source's D3 recommendation/D2 fallback, and replace the open choice with a justified final selection only when one is made.
4. **Artifact and validation:** In the completed assignment, show the selected artifact, a normal and attack comparison, independent evidence, measured timings, and limits. A mock-data demo is optional; nothing is available to demo from this drafting task.
5. **Engineering action and next work:** Use the short engineering message, identify proposed owners, explain operational friction, and discuss remaining validation. Leave room for interviewer questions throughout and questions for them at the end.

## Before treating this as a completed submission

- Resume the second-path requirement when the author chooses; it remains deferred in the current scope.
- Select one control, finalize the corresponding rationale/message, and build the small artifact in a later task. Do not expand the assignment into a requirement to implement the entire platform or all four options.
- Validate with representative positive/negative evidence; report actual results and TTD, or explicitly state which claims remain unvalidated. Keep mock replay and live sandbox outcomes distinct.
- Complete the AI note with actual prior prompts/errors and the candidate's personal checks. AI-generated consistency checks are not manual verification by the candidate.
- After selecting one option, condense and format the final 2–3-page write-up, attach the built material, and prepare the walkthrough. Preserve the complete explanations here as supporting material. A repo, Gist, or zip is accepted; no publishing occurs in this task.
