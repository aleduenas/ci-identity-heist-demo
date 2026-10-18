# Operation Leaky Pipeline — expanded assignment draft

This case study explores how stolen AI coding-agent credentials could turn an ordinary code change into deployment access and, through a replaced backend application, access to customer financial data.

**Status:** Expanded working draft, 2026-10-17. The concept remains unchanged; no control is selected, built or validated. The second attack path is deferred at the author's direction. This standalone explanation is planning material: the eventual submission must be edited and formatted to the assignment's 2–3-page limit after selecting a control.

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

## Why normal code review might not stop this attack

Normally, a software engineer or coding agent pushes a proposed change, automated checks provide feedback, and a person reviews it before merging. A trusted release then builds and deploys the approved application. PR testing and deployment serve different purposes and should not be assumed to need the same access.

In the hypothesis, the attacker does not bypass the merge approval. They exploit the earlier moment when the test job runs code from the PR. A **CI runner** is the machine executing those automated checks. If its job can obtain the AWS deployment role, the attacker-controlled script can try to use that role before review.

The attacker starts as an external credential thief impersonating a coding agent, not as an AWS administrator or a privileged support employee. SAML sign-in, protected main, IAM and Kubernetes permissions, ticket association and human review remain part of the scenario. The assumed failure is narrower: unreviewed PR execution can reach deployment privileges, and that deployable application already has legitimate data access.

The six conditions to validate are PR editing rights, pre-review execution, access to the deployment role, permission to change the backend, inherited application-data access, and outbound connectivity. Accepted image retrieval and private-cluster reachability also matter for a sandbox demonstration. An existing safeguard stopping a step is a finding, not a reason to claim the remainder happened.

## Four control options remain open

Each option watches a different action in the same attack. The eventual assignment needs one small working artifact; it does not require implementing all four.

**[D1 — Notice changes to code the PR checks execute](../d1-pr-executable-change/draft.md).** A detector would inspect the changed files and their actual diff when an unreviewed PR receives a new commit. It would flag changes to the build/test scripts or other inputs that the selected job executes, with the commit, actor and run link for investigation. Ordinary tests and application code are executable too: a changed file is not proof of malicious intent. The detector must be controlled outside the branch the attacker can edit. A separate later experiment could require approval before a privileged job runs.

**[D2 — Notice PR tests obtaining deployment permissions](../d2-pr-role-assumption/draft.md).** AWS Security Token Service (**STS**) issues temporary role credentials. AWS **CloudTrail** records AWS activity. In the proposed OIDC setup, GitHub uses OpenID Connect identity information to request an AWS role instead of storing long-lived AWS keys. D2 would connect the role-assumption event to independently obtained GitHub run information and alert when the deployment role is used by PR validation rather than a trusted release. A job-chosen session name is not trustworthy proof of origin; CloudTrail must not be assumed to contain every original PR field. Separately restricting verified OIDC trust could prevent that role grant.

**[D3 — Notice backend replacement without a trusted release](../d3-unexpected-deployment/draft.md).** Kubernetes audit events record requests to change the backend's **Deployment**, the resource controlling its running containers. D3 would compare successful changes with an independent trusted-release record. The same deployment role can make both good and bad changes, so identity alone is insufficient. A matching release needs credible target, change and timing context; a missing release feed is an evidence problem, not automatic proof of an attacker. The focused test requires an accepted update and an observed image change.

**[D4 — Notice or block unexpected outbound traffic](../d4-unapproved-egress/draft.md).** **Egress** means traffic leaving the application. A supported network observer, such as a configured egress proxy, would associate the backend's connection with an unexpected destination and produce an alert. The test uses invented customer records and an owned HTTPS receiver. Destination metadata alone does not establish which records were transferred; receiver evidence confirms whether the synthetic payload arrived. A separate restriction could block unneeded destinations, provided required database, identity and external integrations still work.

The immutable concept recommends **D3**, because it detects successful misuse of permission the deployment identity actually has. It retains **D2** as a narrower fallback if independent release correlation proves too cumbersome. That recommendation remains conditional; D1 and D4 are still available and no final selection is made here.

## How the selected option would be tested

Begin with a normal action, then a harmless simulation of the specific attacker behavior. Keep the detector and its retained evidence outside the editable PR and replacement application. Use only an owned or authorized sandbox and synthetic data; never test, scan or interact with Relay systems, domains or employees.

| Option | Normal comparison | Harmless attack simulation | What a detection pass requires |
| --- | --- | --- | --- |
| D1: N1 / A1 | Routine PR work, with legitimate executable edits correctly understood | Marker change to the exact script the PR job executes | Evidence the changed script ran, plus an independent, actionable executable-change alert |
| D2: N2 / A2 | Trusted release obtains the deployment role | PR-validation job obtains that role and performs a harmless identity check | Successful role grant, reliable independent PR linkage and an alert |
| D3: N3 / A3 | Trusted workflow deploys a harmless version | Same role changes the image without a matching trusted release | Accepted change, resulting image, independent release comparison and an alert |
| D4: N4 / A4 | Normal operations use required destinations | Backend sends an identifiable invented payload to our receiver | Attributed outbound event and alert; receiver receipt reported separately |

For each selected pair, retain sanitized source events, context, the detector's decision and an inspectable alert or investigation result. A log entry alone is not a passing detection. Explain legitimate alerts and whether an engineer or analyst can identify the actor, target, change and relevant run. One pair does not establish a production false-positive rate.

Record the action time, first searchable-log time and first independent alert time separately in UTC. **Time to detect (TTD)** is alert availability minus the relevant attacker-action time: PR push for D1, role assumption for D2, accepted backend change for D3, or first malicious outbound attempt for D4. **Ingestion delay** is first searchable-log time minus action time. These measurements distinguish a rule that processes quickly from a log source that arrives late.

A runnable mock-data replay can demonstrate how the rule classifies supplied normal and attack records. It cannot establish live GitHub/AWS delivery, cloud latency or full-chain viability. Those require actual sandbox observations and should be reported only if collected.

Optional prevention comes afterward in a separate run: D1 privileged-job approval, D2 role-trust restriction, or D4 supported egress restriction. D2/D4 retain the concept's B2/B4 labels. Verify the forbidden action did not take effect and normal behavior still works. If a gate stops the run, later stages are unobserved. An alert after the receiver gets the payload is detection, not prevention. All outcomes and timings remain unmeasured.

## Draft message for the engineering channel

> We are planning a sandbox exercise for a hypothetical route from stolen AI coding-agent credentials to customer data. An attacker could change a PR's build/test script, have automated checks execute it before review, and, if that job can obtain deployment access, replace an EKS backend that already has customer-data access. Human merge review would not by itself stop the earlier CI execution. We have not demonstrated this route at Relay.
>
> Proposed change: select one independent check for executable PR changes, unexpected deployment-role use, backend changes without a trusted release, or unexpected outbound traffic. The concept recommends the backend-change check if trustworthy release matching is available; no option is selected yet. The initial work would detect the action. Blocking privileged execution or outbound traffic would be a separately tested follow-up.
>
> Software/application engineers: identify the build/test scripts and hooks PR checks execute, show a routine change for comparison, and explain the backend's normal data operations and external integrations. Platform/CI owners: confirm which jobs can obtain deployment roles, what changes those roles can make, how the private cluster is reached, and which run/release/audit or network records exist outside the editable PR. Help define the normal release comparison and, if relevant, emergency changes and rollbacks.
>
> Security: name the alert owner and destination, agree the expected signal and triage outcome, and retain sanitized evidence. Done for the selected check means a harmless simulated attacker action produces an independently retrievable alert with enough context to investigate, normal work is unflagged or correctly triaged, and action/log/alert times are recorded. Ordinary unprivileged PR feedback should remain available. Any later prevention claim must also show the forbidden action was stopped while normal releases or integrations still work.

## AI usage note

Codex was asked to map the author's concept to the assignment without changing the concept, preserve all four options, and draft the validation and engineering handoff. AI-assisted review compared the drafts with the supplied instructions; those checks were document review, not technical validation.

The first AI drafts relied on unexplained references to numbered attack steps and gave an engineering message that was too vague to act on. The author flagged both problems during readability review. This revision includes the full attack in each standalone draft, explains the technical terms and normal workflow, and names software, platform and security actions with completion criteria.

This draft leaves inferred GitHub provenance, deployment permission alone, and unsupported timing unverified. No candidate-led technical validation is recorded from this drafting task, and the author's readability feedback must not be presented as such. Earlier research prompts, any other actual AI errors, and the candidate's eventual personal checks still need to be recorded truthfully for the final submission.

## Next work and source documents

After choosing a control, build only the focused artifact, run the selected normal/attack comparison, record actual results and limitations, and prepare the short presentation. With more time, evaluate the other hypotheses and improve handling of legitimate changes, missing telemetry, emergency releases and rollbacks. The second attack path remains deferred.

The [immutable concept](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md) remains the authority for the narrative and hypotheses; the [take-home instructions](../take_home.md) define the deliverables. The [assignment guide](../assignment-draft/README.md) maps each requirement. The [repository architecture](../../architecture.md) and [implementation ledger](../../implementation-status.md) describe a synthetic lab and local/static checks, not a validated live attack. No AWS apply or live EKS acceptance is recorded. Before submission, finalize the AI note, chosen artifact and rationale, then format and verify the 2–3-page write-up.
