# D4 — Detect when the backend sends traffic to an unexpected destination

An attacker steals a coding agent's GitHub credentials, uses unreviewed PR code to obtain deployment access, and replaces the backend application. The replacement uses the application's existing database access to retrieve records and tries to send them to an external receiver. D4 would detect that last outbound connection; a separate optional control would try to stop it.

**Status:** Expanded planning draft, 2026-10-17. No observer, detector, receiver, or restriction has been built or tested for this option. All outcomes and timings are unmeasured. D1–D4 remain open. This supporting document explains a candidate for the eventual short assignment write-up.

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

## Where D4 acts and what normal traffic looks like

D4 covers the final three actions above: the changed backend retrieves records, attempts an HTTPS transfer, and may deliver those records outside the environment. It asks whether we can independently notice the backend contacting a destination that its owners never approved. It is the same attack chain as the other options, observed at its last stage.

The backend must already access its database to serve legitimate requests. Its running container receives the application's normal runtime configuration and identity. A deployment role may therefore lack direct database access while still being dangerous: permission to replace the application can let an attacker run different code with the application's access. This draft assumes that replacement and data access work; those earlier steps need separate validation.

An **outbound connection**, also called **egress**, is traffic the application sends to another service. Normal outbound traffic includes database requests and any approved external API integrations. HTTPS encrypts web traffic; it does not establish whether the destination is appropriate. A **webhook** here is simply a web endpoint that accepts a request containing data. In the exercise, we would own that receiver and send only invented records.

The proposed alert condition is therefore **this backend contacted an unapproved destination**, not **this backend used HTTPS**. A legitimate new integration can produce the same condition, so the alert is a reason to investigate. Network destination evidence alone also does not prove that customer records were sent.

## The small deliverable this option would produce

If selected, D4 would produce a focused destination-checking rule or small detector, representative normal and attack examples, and instructions for reproducing the comparison. Its input would come from a supported observation point outside the application. Its output would identify the application, observed destination, event time, reason for escalation, and evidence an engineer can inspect.

The normal-destination list must come from the application and platform owners. It would identify required services and how their destinations are represented in the chosen telemetry. A hostname-based expectation cannot be silently compared with an IP-only record: a domain may use changing addresses, and several services may share infrastructure. The chosen observer determines which comparison can actually be supported.

The detector would operate as follows:

1. Receive an outbound connection event from the independent observer.
2. Establish whether it belongs to the backend under test, using the available workload identity and network context.
3. Extract the destination that the observer actually records, such as a hostname or IP address and port.
4. Compare it with the documented destinations required by that backend.
5. Return **expected**, **unexpected destination**, or **insufficient evidence**. Missing workload attribution or unusable destination data must remain visible as a coverage gap.
6. For an unexpected destination, create a retrievable security alert or investigation result and send it to an agreed owner.

An illustrative result might read: “The sandbox backend contacted exercise-receiver, which is absent from its approved integrations. The observer attributed the connection to pod mock-api-b in the sandbox namespace. Review the network event and recent deployment. Payload delivery is unknown until receiver evidence is checked.” These names and this result are examples, not observed findings.

## What observation and independent evidence mean

An **observation point** is a component that can actually see the connection. One source-supported option is an **egress proxy**: a separately managed service through which outbound requests are routed and which records those connections. Another is a network telemetry system that explicitly supports the required traffic and attribution. We have not selected or deployed either.

Merely configuring an application to use a proxy does not prove that all of its traffic passes through it. Before claiming coverage, the test must show that the exercised connection traverses the observer and document any direct route around it. A detector cannot alert on traffic it never sees.

**Workload attribution** means connecting a network record to the particular backend container or pod that originated it. A Kubernetes pod is the running unit containing the application container. A record showing a shared gateway address may identify the environment without identifying the backend. That difference matters: the alert must be about the selected application, not an unattributed Internet connection somewhere in the network.

The evidence has three separate jobs:

| Evidence | What it could establish | What it does not establish alone |
| --- | --- | --- |
| Independent proxy/network event | Observed destination and, where supported, originating workload | Which records were inside an encrypted request |
| Controlled receiver receipt | The identifiable synthetic payload reached our receiver | An independent security detector fired |
| Application/test execution record | The test code ran or attempted an action | Complete network coverage or trustworthy detection |

The collector, rule, normal-destination list, and alert records must be controlled outside the attacker-editable PR and replacement application. Otherwise, the same code we are testing could alter its own evidence or declare its destination approved.

VPC Flow Logs alone generally do not expose HTTPS URL paths or request bodies and may need additional context for pod attribution. We would not present such records as proof of the payload's contents. Likewise, logs written by the modified application cannot be the sole independent security signal.

## Safe validation: N4, A4, and optional B4

These labels identify three planned comparisons for this option. No real Relay system, domain, employee, or customer data would be used. The repository, image, application, database fixtures, receiver, and alert collection would all belong to an authorized sandbox.

Before running anything, we would document the approved destinations, selected observer, routing, attribution method, receiver ownership, synthetic payload marker, and alert owner. We would first verify that the observer can see a known backend connection. If it cannot, the live detector is not ready for validation.

### N4 — Normal application behavior

Run ordinary API operations that use the mock database and exercise each required integration selected for the test. Confirm the operations succeed, collect their independently observed destinations, and verify the detector treats them as expected. Record which integrations were tested; one successful health request does not exercise database access or every outbound dependency.

If normal operations trigger an alert, inspect whether the destination list, attribution, or comparison is wrong, or whether the integration genuinely needs owner review. Do not simply suppress the alert without recording why. This is the practical check that the proposed rule can distinguish useful security signals from routine engineering work.

### A4 — Controlled outbound transfer

Run harmless replacement image B in the authorized sandbox. It would retain the normal application behavior and add the concept's test action: read invented customer records, then send a uniquely marked synthetic payload to our own HTTPS receiver. A receiver absent from the normal integration list represents the attacker's unexpected destination.

Record the first outbound attempt time, the independently observed connection, the first searchable event, the alert, and the receiver result. The receiver should retain the marker and receipt time needed to link the transfer to this test. A mock-database access record, if enabled, would support the separate statement that the image retrieved the fixture records.

Assess four outcomes individually:

| Outcome | Evidence required |
| --- | --- |
| **Attempt made** | Test execution and the corresponding observed outbound action, with a defensible start time |
| **Detected** | A retrievable independent alert identifying the backend and unexpected destination |
| **Delivered** | The controlled receiver recorded this test's synthetic payload marker |
| **Prevented** | Known enforcement stopped the forbidden action, independently evidenced, and the receiver obtained no payload |

The intended detection-mode comparison allows the controlled transfer so that both destination detection and receipt can be assessed. If the alert arrives after the payload, we have demonstrated detection after delivery. We have not demonstrated data-loss prevention.

If the receiver sees nothing, investigate why. A DNS failure, test error, or unreachable receiver could explain non-receipt. Absence alone proves neither detection nor blocking. If an earlier control stops the chain before image B runs, report that boundary and leave A4 untested in that run. A separately staged final-step test can evaluate D4, but cannot establish that the full chain succeeded.

### B4 — Optional destination restriction

After recording the detection comparison, a separate experiment could activate a supported restriction permitting only required outbound destinations. Repeat the same synthetic transfer attempt. Record the effective restriction, independently observed denial, receiver outcome, and alert availability. Repeat N4 to check database access and legitimate integrations still work.

B4 passes only if the forbidden transfer did not take effect, the independent evidence shows enforcement, and normal tested dependencies remain usable. If the receiver obtained the payload, that run does not establish prevention. Restriction is optional; selecting a detector does not silently commit us to a networking change.

## Measurements and what the demo could honestly show

Record separate UTC timestamps for the first malicious outbound attempt, first searchable relevant event, first independently available alert, and receiver receipt if any. Keep references to sanitized evidence for each timestamp.

| Measure | Calculation or assessment |
| --- | --- |
| Time to detect | First independent alert time minus first A4 outbound-attempt time |
| Log ingestion delay | First searchable observer-event time minus that same attempt time |
| Normal-behavior check | N4 alerts, tested integrations, and reasons for any escalation |
| Investigation readiness | Can the recipient identify the backend, destination, time, and reason without trusting application logs? |
| Transfer/prevention result | Receiver marker plus independent allow/deny evidence; assess separately from detection |

All values remain **TBD**. A small N4 sample can report observed false positives, but cannot establish a production false-positive rate. If there is no alert, do not assign a successful detection time. Distinguish missing telemetry from a recorded expected result.

A future mock-data presentation could show the rule returning expected, unexpected, and insufficient-evidence outcomes. Those inputs must be labeled fixtures. Such a demo verifies rule behavior on the examples; it does not verify live proxy routing, pod attribution, encrypted-transfer visibility, delivery delay, or enforcement. Real observation would require the supported collection path and the controlled N4/A4 comparisons above.

## Fit with this repository and remaining uncertainty

The repository's application egress policy permits DNS, Pod Identity access, and broad IPv4 TCP/443. That is not a list of approved webhook destinations. The architecture keeps the EKS API private and provides outbound networking; neither fact establishes that this specific transfer works or is observable. The handoff ledger records no live EKS rollout or CNI-enforcement validation. D4 is proposed instrumentation, not a description of an existing deployed detector.

The main practical questions are who maintains legitimate destinations, which supported observer can attribute this connection, and which routes it misses. Changing domains/IPs, shared gateways, encryption, and new integrations may limit the rule or create review work. These limits must be shown alongside the demonstration.

## Engineering-channel message draft

> **Proposed check: notice unexpected outbound traffic from the backend.** We are evaluating a hypothetical attack in which stolen coding-agent access lets someone change PR code, obtain deployment permissions from CI, and replace our backend. The replacement could use the backend's normal database access to read records and send them to an external web endpoint. We have not established that this chain works here or at Relay.
>
> The proposed first change is monitoring: independently observe where the backend connects, compare that with its approved integrations, and alert the application and security owners about unexpected destinations. HTTPS traffic by itself is normal. The alert must identify which backend made the connection and why the destination is unexpected. Blocking outbound destinations would be a separate proposal after we understand the operational impact.
>
> **Application engineers:** Please list the services the backend must contact, why it contacts them, what kinds of data it sends, and the normal operations that exercise those integrations. Identify who approves a new integration so legitimate changes can update the destination list. Help us prepare invented records and confirm ordinary API behavior still works during the test.
>
> **Platform/infrastructure engineers:** Please identify a supported network observer or proxy, establish which backend traffic actually passes through it, and show how its records identify the originating pod and destination. Document any unobserved route. If we later test restriction, choose an enforcement mechanism that supports the required destinations and verify that database, identity, DNS, and approved integrations continue to work.
>
> **Security and service owners:** Agree who receives the alert, who investigates it, and how that person finds the network event, deployment context, and controlled receiver result. Keep the detector and approval list outside application/PR control.
>
> We would call the detection test complete when normal tested integrations remain usable, a controlled transfer to our owned receiver produces an independently retrievable alert with workload and destination evidence, and we can report measured detection time alongside whether the receiver got the synthetic payload. Any optional blocking result must additionally show enforced denial, no received payload, and working normal integrations. Nothing has been built or measured yet.

## Relationship to the other options and source documents

D4 remains one candidate on the single immutable attack chain. The concept's recommendation to start with D3, with D2 as a narrower fallback, is unchanged. A second attack path remains deferred at the user's request. This document adds explanation and a proposed validation contract; it does not select an implementation or invent findings.

Sources: [Immutable concept, D4 and validation/handoff sections](../Relay_AI_Agent_to_EKS_Tabletop_Attack_and_Detection_Plan.md) · [Take-home instructions](../take_home.md) · [Assignment map](../assignment-draft/README.md) · [Submission draft](../submission-draft/draft.md) · [Repository architecture](../../architecture.md) · [Implementation status](../../implementation-status.md) · [Current application egress policy](../../../deploy/kubernetes/base/network/app-egress.yaml).
