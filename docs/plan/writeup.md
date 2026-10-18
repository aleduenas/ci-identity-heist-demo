# Operation Leaky Pipeline — Case Study Write-up

**Author:** A. Dueñas · **Date:** 2026-10-18 · **Scenario:** Mybank, Purple Team (P1/P2)

> **Scope and safety.** Everything here runs in a personal, authorized AWS sandbox with invented
> customer records. No real system, domain, or employee was touched. The sandbox is named
> `mybank-sandbox-*` in code; "mybank" is the synthetic financial backend used throughout. The
> attack, detection, and prevention described below were executed and observed live — timings and
> outcomes are measured, not promised. The *AI-usage* section is written separately by the author.

---

## 1. Intro

### Summary of the task

Mybank ships code daily through **GitHub → CI/CD → EKS**, on AWS, behind SAML SSO, with a small number
of employees holding elevated customer-data access. Engineers increasingly use AI coding assistants and
agentic workflows, so more people — not all with a security background — are writing and deploying code.

The Purple Team wants to know whether a compromised developer laptop or CI job would be **caught, and
how quickly**. The assignment asks us to:

1. Describe **two realistic attack paths** from the developer environment to customer/financial data.
2. Pick one and build a **small, working control or detection** for it.
3. Write a **validation plan**: how to safely simulate the attack and what to measure.
4. Write a **summary an engineering team could act on**.

This write-up covers one attack path end-to-end, the detection and prevention we built for it, how we
validated them in a live sandbox, what the engineering team needs to know, and where the model is
simplified. We deliberately chose an attack where the attacker's actions are *individually authorized* —
so the interesting question is detection, not just "tighten the IAM policy."

### Assumptions made

These are exercise assumptions. They are the conditions the attack needs to complete; they are **not**
claims that Mybank has these gaps. We mark each as *assumed* or *observed in sandbox*.

- **A1 — Stolen agent credentials grant PR-level GitHub access.** A phished AI-coding-agent token can
  read private repos, create branches, push code, and open/update pull requests, but cannot approve or
  merge. *(Assumed; in the sandbox the operator authored the PR to stand in for this.)*
- **A2 — PR checks execute PR-supplied code before human review.** Updating a PR triggers CI that runs
  build/test scripts from the PR branch. *(Observed in sandbox.)*
- **A3 — A PR-triggered job can obtain the AWS deployment role.** The deploy role's OIDC trust policy
  accepts the `pull_request` context, so `sts:AssumeRoleWithWebIdentity` succeeds from a PR job.
  *(This is the single hypothesized misconfiguration; observed in sandbox once set.)*
- **A4 — The deploy role can modify the backend's EKS Deployment** but **cannot** read the customer
  database directly. *(Observed in sandbox.)*
- **A5 — The backend application's own identity can read the customer tables.** Replacing the
  application lets the attacker inherit that data access (the deploy→data pivot). *(Observed.)*
- **A6 — The EKS API is reachable from CI.** A public, IAM/RBAC-authenticated endpoint, common where
  pipelines deploy from GitHub-hosted runners. The vulnerability is not the endpoint; it is PR jobs
  being able to get deploy credentials. *(Configured in sandbox for a fully-remote demo.)*
- **A7 — Standard safeguards remain in place:** human merge review, protected `main`, SAML SSO, IAM and
  Kubernetes RBAC, and ordinary audit logging. The hypothesized failure is narrow and specific.
- **A8 — Synthetic everything.** Two invented customers (`acct-alice`, `acct-bob`), a lab repo, and a
  lab AWS account. No real infostealer, no real agent, no real data.

---

## 2. Attack path 1 — *(placeholder)*

> **TODO (author to complete).** Second realistic path to customer data through the developer
> environment, described in the same plain-English + MITRE form as path 2, then compared against it.
> Candidate paths to choose from: a **leaked long-lived GitHub Actions secret / static AWS access key**
> committed or exposed in CI; a **malicious npm/dependency** pulled into the build; or a **stolen
> developer SSO/session token** from a laptop. Left intentionally empty for now.

---

## 3. Attack path 2 — the one we built for

### In plain English

An attacker phishes a junior developer's **AI-coding-agent GitHub token**. That token can't merge code,
but it can **open a pull request** — and Mybank's CI runs automated tests on a PR *before* anyone reviews
it. The attacker puts their own code inside a test/build script, so it runs on the CI runner. That CI
job asks GitHub for an OIDC token and uses it to assume Mybank's **AWS deployment role** — because the
role's trust policy currently accepts PR-triggered jobs. With deploy credentials, the job reaches the
**EKS** cluster and **replaces the backend application's container** with a reader of the customer
tables. Because the replacement keeps the backend's service account, it **inherits the application's own
data access** — the pivot from "can deploy" to "can read customer data." The job then dumps customer
records (names, emails, balances) straight into the Actions log, and rolls the app back.

The whole thing happens **inside GitHub Actions and the AWS API**. The attacker never touches Mybank's
repo host or AWS console directly; their only compute is the GitHub-hosted runner they drive through the
PR. Two trust boundaries fall: **GitHub code-editing access → AWS deploy access**, then **deploy access
→ customer-data access through the application**.

```text
stolen agent token ─► open PR ─► CI job runs PR code ─► AssumeRoleWithWebIdentity (deploy role)
                                        │                         [BOUNDARY 1: CI → AWS]
                                        ▼
                         eks update-kubeconfig ─► kubectl patch backend Deployment
                                        │
                                        ▼
                    replacement keeps the app's service account / Pod Identity
                                        │               [BOUNDARY 2: deploy → data]
                                        ▼
             reads customer tables ─► dumps acct-alice / acct-bob ─► printed in the run log
```

### Full MITRE ATT&CK path

Following the Enterprise matrix left to right. Conditional entries are marked; a technique mapping is a
scenario-level fit, not proof every technique fired in every run.

| # | Tactic | Technique | How it applies here |
|---|---|---|---|
| 1 | Reconnaissance | — | Broad infostealer campaign; no specific recon technique asserted. |
| 2 | Resource Development | T1608.001 — Upload Malware | Staging the infostealer delivery (method unspecified). *Conditional.* |
| 3 | Initial Access | **T1078.004 — Valid Accounts: Cloud Accounts** | Stolen agent token used to reach private GitHub resources under a legitimate identity. |
| 4 | Execution | **T1059.004 — Unix Shell** | Modified CI build/test script runs on the shell-based runner. |
| 4 | Execution | **T1610 — Deploy Container** | Replacement backend container deployed via EKS. |
| 5 | Persistence | — | No persistence deliberately established. |
| 6 | Privilege Escalation | **T1548.005 — Temporary Elevated Cloud Access** | PR job obtains the deploy role it should not — the first boundary crossing. |
| 7 | Stealth | T1078.004 | Activity looks like the authorized agent; a release-looking session name is used. |
| 8 | Defense Impairment | — | Logging/defenses not disabled. |
| 9 | Credential Access | T1528 — Steal Application Access Token | Infostealer takes the agent token; the runner also exposes temporary AWS creds. |
| 10 | Discovery | T1526 — Cloud Service Discovery | Enumerate what the CI role can reach. |
| 10 | Discovery | T1613 — Container and Resource Discovery | Identify the EKS cluster, namespace, and backend Deployment. |
| 11 | Lateral Movement | T1550.001 — Alternate Auth Material: App Access Token | *Conditional* — only if creds are reused outside the runner. Omit from results if they aren't. |
| 12 | Collection | T1213.003 — Data from Repos: Code | Read source/config to find the data path. |
| 12 | Collection | **T1213.006 — Data from Repos: Databases** | Replaced app uses its legitimate connectivity to read customer records. |
| 13 | Command and Control | — | No persistent C2 channel. |
| 14 | Exfiltration | T1567.004 — Exfiltration Over Webhook | *Not performed in this demo* — records are printed to the run log, proving read access, rather than sent out. |
| 15 | Impact | — | Objective is data theft, not disruption. |

**The transitions that actually matter in our demo:** T1078.004 → T1059.004 → **T1548.005** →
T1610 → **T1213.006**. The bolded ones are the two boundary crossings; T1548.005 is where we detect.

### Why this attack is realistic, and why it's possible

- **AI agents mean more PRs from more identities.** The scenario explicitly calls out agentic workflows.
  An agent token is a credential like any other — phishable, stealable from a laptop, leakable in a log.
  It's a *low-privilege* credential, which is exactly why it's underestimated: it can't merge, so it
  feels safe.
- **PR CI runs untrusted code by design.** Running tests on a proposed change *before* review is the
  normal, useful behavior of CI. The attacker doesn't bypass merge review — they exploit the earlier
  moment the runner executes PR-supplied code. Human review is intact and irrelevant to this step.
- **Deploy-capable OIDC trust is a common real misconfiguration.** GitHub OIDC → AWS is the modern,
  recommended pattern (no long-lived keys). But the trust policy's subject condition is easy to write
  too loosely — e.g., matching the whole repo rather than `ref:refs/heads/main` — so PR jobs quietly
  qualify for the deploy role. This is the single assumption the whole chain hinges on.
- **The deploy→data pivot needs no database credential.** The attacker never steals a privileged
  support employee's access. They replace an application that *already* has legitimate data access and
  let Kubernetes hand the new container the same service account. Separation of "deploy" and "read data"
  permissions is defeated because deploying *is* a way to run code as the data-reading identity.
- **It's fully remote.** No malware on a Mybank host, no inbound access — just a PR and the AWS API over
  GitHub-hosted runners. That is a very low bar for an external attacker holding one stolen token.

---

## 4. Rationale — why we chose attack path 2

We built for the **CI → AWS credential-assumption boundary** (step 15, T1548.005) because it makes a
genuinely good tabletop, not because it's the easiest to block:

- **Every authorized action, yet clearly malicious.** The PR job is *allowed* to assume the role (under
  the assumed trust misconfig), the role is *allowed* to patch the Deployment, and the app is *allowed*
  to read the tables. An `AccessDenied`-style detector catches none of this. The interesting security
  question is: can we tell a *legitimate* use of the deploy role from a *malicious* one when both use
  the same role and the same API call? That forces a real detection design, not a permissions lecture.
- **It's a mandatory chokepoint.** Every variant of this data-theft chain — regardless of which script
  the attacker edits, which image they deploy, or how they exfiltrate — has to cross this one boundary
  to get cloud capability. Detecting here covers the general case, not one specific payload.
- **There is independent, signed evidence.** AWS CloudTrail records the credential issuance with a
  GitHub-signed subject, outside anything the attacker can edit in their PR. That gives us a trustworthy
  artifact and a clean normal-vs-malicious comparison (`pull_request` vs `main` context).
- **It is the earliest point of real capability gain.** Before this step the attacker has only a GitHub
  token; after it they have production deploy power. Catching at the first capability gain is the most
  valuable place to put one detector if you can only build one.
- **It demonstrates both halves of purple-team value.** The same boundary supports a crisp **detection**
  (correlate the credential grab) *and* a crisp **prevention** (fix the trust policy), so we can show
  "catch it in ~1 min" and "stop it before any credential exists" back to back on the same stage.

We are not claiming this is the only path worth defending — it's the one that best exercises detection
judgment in a 1-hour demo.

---

## 5. The detection

### In plain English — how it works

The detection watches **AWS's own record of who was handed deployment credentials**. Whenever the deploy
role is assumed, AWS writes a CloudTrail event that includes a GitHub-signed description of the job that
asked for it — which repository, which run, and crucially whether the trigger was a **pull request** or
a push to **main**. A small monitor, running on the defender's machine (outside GitHub), reads that
event, independently looks up the same run in GitHub's API to confirm the details match, and **alerts
when a pull-request job obtained the deploy role**. A normal release from `main` produces no alert.

Because it reads a signed subject and re-checks it against GitHub's own run record, it **ignores the
session name the attacker chose** (our demo deliberately names the session `release-looking-demo`, and
the detector is not fooled). When it can't independently confirm the context, it says
`context_not_verified` ("investigate") rather than quietly trusting it.

### Where it sits in the MITRE path, and why there

It sits at **T1548.005 — Temporary Elevated Cloud Access**, the credential-issuance event
(`sts:AssumeRoleWithWebIdentity`), i.e. **Boundary 1 (CI → AWS)**.

Why here specifically:
- It's the **earliest** point where the attacker gains capability beyond the stolen GitHub token.
- It's a **chokepoint** every version of the chain must pass through.
- It's the first point with **independent, attacker-proof evidence** (CloudTrail + GitHub's run API).
- It's before any customer data is touched, so an alert here is well-positioned for response.

### How it works technically

- **Signal source:** CloudTrail `AssumeRoleWithWebIdentity` management events for the one deploy role,
  read via the regional `LookupEvents` API — no new trail required (always-on Event History is enough).
  The collector pages results, respects the 2-req/s quota, filters to the exact role, and dedupes by
  event ID. ([`scripts/d2/collect.py`](../../scripts/d2/collect.py))
- **Independent correlation:** for each successful event it reads
  `responseElements.subjectFromWebIdentityToken`, verifies the expected GitHub OIDC provider/audience
  and the issued-role ARN, parses the signed subject for `run_id`/`run_attempt`/`event_name`, then calls
  `GET /repos/{owner}/{repo}/actions/runs/{id}/attempts/{n}` and checks the **immutable owner and repo
  IDs**, exact run/attempt, and event type match. ([`scripts/d2/detector.py`](../../scripts/d2/detector.py))
- **Decisions:** `pr_role_misuse` (PR context, verified) → **alert**; `expected_release` (main context +
  the expected workflow + branch `main`) → no alert; `assumption_denied` (AWS refused — the prevention
  fired — linked to its run via the rejected subject in `userIdentity.userName`); `context_not_verified`
  (missing/conflicting/unavailable evidence) → investigate, never a trusted match.
- **Out-of-band authority:** the collector, its GitHub read token, and the authoritative detector code
  live **outside** the PR-editable branch and run in a separate trusted process, so a compromised PR
  can't disable or spoof the detector.
- **Paired prevention:** `scripts/d2/set_trust block-pr` reads the role's live trust policy, drops the
  `pull_request` subject from the `StringLike` condition, and writes it back with
  `UpdateAssumeRolePolicy`. The PR subject then matches no allowed pattern, so AWS denies the grant
  *before any credential exists*; the `main` patterns are untouched, so releases still work.

### Advantages

- **Attacker-proof evidence.** Keys on AWS's signed subject + GitHub's run record, not on anything the
  PR can edit — and explicitly not on the session name.
- **Out-of-band.** Runs outside GitHub; a compromised PR job cannot turn it off or tamper with it.
- **Earliest meaningful catch, at a chokepoint.** Alerts at the first capability gain, before data is
  touched, on a boundary every variant must cross.
- **Low expected false-positive surface.** It distinguishes by *context* (`pull_request` vs `main`)
  under the *same identity*; in a correctly configured environment, PR jobs never get the role at all,
  so a positive is essentially the vulnerability itself.
- **Cheap and fast to stand up.** No new CloudTrail trail, no SIEM required; read-only GitHub token.
  Observed time-to-detect ~31 s in the live run.
- **Fails safe.** Unverifiable context becomes a visible "investigate," never a silent pass.
- **Comes with a real fix.** The same boundary has a one-line trust-policy prevention that closes the
  hole entirely while leaving normal releases working.

### Disadvantages

- **Detection ≠ prevention.** On its own it doesn't stop the attack; in the detection-only run the data
  is still read in the window before response. (This is why we also built the trust-policy block.)
- **Latency, not real-time.** CloudTrail ingestion plus 15 s polling gave ~31–83 s in the sandbox;
  worst case can be minutes. It's near-real-time, not instant.
- **Depends on GitHub correlation.** Needs a separate `Actions: read` token and the GitHub API being
  reachable; if the run lookup fails, the honest answer is `context_not_verified`, not a confirmed
  alert.
- **Requires OIDC run-context in the subject.** The repo-wide OIDC subject must include
  `run_id`/`run_attempt`/`event_name`; otherwise the detector can't correlate and returns an evidence
  gap. That's a coordinated configuration change.
- **Polling, single role, single op.** It polls rather than being event-driven (EventBridge would be
  better but needs an active trail), and it watches exactly one role and one STS operation. It does not
  cover credential *reuse* outside the runner (T1550.001) or other deploy-capable roles.
- **Small sample.** Three live comparisons don't establish a production false-positive rate or latency
  distribution.

### Why the trade-offs are worth it

The core trade-off is **latency and "detect-not-block" in exchange for a trustworthy, general,
early-chokepoint signal**. That's the right trade for a purple-team control because: (1) the evidence is
independent and can't be spoofed, so an alert is *actionable* — it carries the role, the run link, and
the context an analyst needs; (2) catching at the first capability gain beats catching at exfiltration;
and (3) detection generalizes (it still sees novel payloads, other images, other exfil methods) while
prevention closes the one known hole. Running **both** — detection for the general case, the trust-policy
fix for this specific case — is strictly better than either alone, and the sandbox shows them working
together on the same boundary.

---

## 6. The validation

### 1. The live test (what we actually ran)

In the sandbox we ran matched pairs against the **same role and the same STS operation**, with the
monitor started before the actions so its polling bounds the timing:

- **N2 — legitimate baseline.** A `main` dispatch of the release workflow assumes the role →
  `expected_release`, **no alert**.
- **A2 — the attack.** An unreviewed PR changes only a harmless marker in the CI-executed probe and
  pushes → the PR job obtains the deploy role → `pr_role_misuse`, **alert** "Deployment credentials
  issued to PR validation." Observed **TTD ≈ 31 s**.
- **Spoof check.** The job keeps the `release-looking-demo` session name during A2; the detector still
  identifies PR context from the signed subject and run record. The label has no effect.
- **B2 — prevention.** Switch the role's trust to main-only and repeat: the PR request is **denied**
  (`assumption_denied`, still linked to its run via the rejected subject), while **main still
  succeeds**.
- **Context gap.** With the GitHub lookup deliberately unavailable, both events return
  `context_not_verified` → "investigate," never a fabricated trusted match.

We record **event time, first-searchable-log time, and first-alert time separately in UTC**, and report
**TTD = alert time − AWS event time** and **ingestion delay = first-searchable − event time**. Evidence
is sanitized (no JWT, no credentials object, no access-key ID or session token). See
[`docs/d2/evidence.md`](../../docs/d2/evidence.md).

A "pass" requires an actual retrievable alert with enough context to investigate — a raw log line is not
a pass — and the legitimate run must *not* escalate.

### 2. Back-testing against legitimate PRs (false-positive estimate)

Three live samples can't establish a false-positive rate. To estimate one safely and without touching
production, we would **replay historical CloudTrail `AssumeRoleWithWebIdentity` events** for the deploy
role — weeks or months of real merges, releases, re-runs, retries, `workflow_dispatch`, and matrix jobs
— through the detector offline and count how many legitimate events it would have flagged.

What we expect and why it's a good measure:
- In a correctly configured environment, **PR jobs never obtain the deploy role at all**, so the
  detector's positive class (`pr_role_misuse`) is effectively "the vulnerability occurred." Backtesting
  mainly confirms the rule doesn't misfire on the *legitimate* positive-adjacent cases: main releases,
  re-run attempts, dispatch vs push, and parallel jobs should all land as `expected_release`.
- It also exercises the `context_not_verified` path on real traffic — how often does legitimate activity
  fall into "investigate" because of a transient GitHub API failure or a subject-format change? That
  number is the real operational noise, and it's the one worth driving down before paging anyone.

Caveat: a replay corpus validates *rule logic and FP behavior*, not live cloud latency or full-chain
viability — those need live observation, which the live test above provides.

### 3. How else we would measure the detection

- **TTD and ingestion-delay distributions** over many runs (p50/p95), not three samples — separating
  "rule is slow" from "log source arrives late."
- **Precision/recall on a labeled replay corpus** mixing legitimate and simulated-malicious events.
- **Investigation readiness:** can an analyst, from the alert alone, name the actor/run/role/context
  without relying on attacker-controlled data? (Yes, by design — but measured, not assumed.)
- **Robustness tests:** session-name spoofing (shown), alternate subject formats, environment-scoped
  OIDC, and deliberate GitHub-lookup outages.
- **Coverage:** does it also record denials (prevention working)? Yes — `assumption_denied`, linked to
  its run.
- **Alert volume in monitor-only mode** before enabling paging, to baseline noise.
- **Drift detection:** alert if the OIDC subject template changes shape, which would silently blind the
  correlation.
- **Mean-time-to-respond** once alerted — the human half of the loop.

---

## 7. How this affects the engineering team

*Written for both security and non-security engineers — including strong developers who may not work in
infrastructure day to day. No action needed from most of you; here's the honest picture.*

**What's going on, in one paragraph.** When you open a pull request, our automated checks run your
proposed code *before* anyone reviews it. That's normal and useful. The subtle risk is not your code
review — it's what the machine running those checks is *allowed to do* in AWS. If a PR's test job can
grab the credentials we use to deploy to production, then a pull request nobody approved can reach
production systems. In our sandbox we showed exactly that: an unreviewed PR obtained the deploy
credentials, swapped the running backend for a version that reads the customer tables, and printed
customer records — all from inside GitHub Actions.

**What you need to be aware of.**
- PR checks execute code from the branch. Treat the CI runner as something an attacker could be driving
  if a token leaks — because "open a PR" is a low bar.
- The dangerous capability is a *CI job being able to assume a deploy-capable AWS role*, not the code
  review itself. Review is intact; it just happens after the risky step.
- A stolen agent/CI token that "only" opens PRs is not low-risk if PR jobs hold cloud power.

**What (if anything) you'd need to change.**
- For most application engineers: **nothing in your day-to-day.** Keep opening PRs as usual; unit tests,
  lint, and ordinary checks are unaffected.
- For platform/CI owners: deploy roles should be assumable **only from protected `main`**, never from
  `pull_request`. The stronger version is **GitOps**, where CI holds no standing deploy credentials at
  all. And it's worth scanning IAM/Terraform trust policies for any that admit `pull_request`.
- If a PR job genuinely needs cloud access (e.g. integration tests), it should use a **separate,
  read-only, scoped role** — never the deployment role.

**Changes you might notice.**
- After we tighten the trust policy to main-only, any PR job that tried to assume the **deploy** role
  will now fail with `AccessDenied`. That failure is expected and correct; it means the guardrail is
  working. If it breaks a workflow you own, that workflow was relying on deploy credentials from a PR —
  tell us and we'll give it a properly scoped alternative.
- Normal releases from `main` are **unchanged**.
- We're running a read-only monitor (CloudTrail + the Actions API). It adds **no required check** to
  your PRs and doesn't change your workflow; initially it only watches.
- There's a one-time, repo-wide OIDC setting change (adding run context to the token subject). Platform
  will coordinate it; it's invisible to application work.

**Anything else.**
- Keep "test" permissions and "deploy" permissions separate — being able to deploy is effectively being
  able to run code as whatever the deployed app can access.
- Emergency fixes and rollbacks should still go through `main`, so they stay covered by the guardrail
  and don't become a new bypass.
- If you use AI agents with repo tokens, treat those tokens like any other secret: short-lived, least
  privilege, and rotated if anything looks off.

**What we need from you:** platform/CI owners to confirm which jobs can assume which roles and help us
roll out main-only trust without breaking legitimate work; application owners to flag any PR job that
currently depends on cloud credentials so we can re-scope it. Everyone else: no action.

---

## 8. Limitations

### Alternatives per section (and how we'd address them)

**Attack path.** We built the CI→AWS boundary (D2). Alternatives were D1 (alert on executable CI-script
changes to an unreviewed PR), D3 (unexpected EKS Deployment change without a matching release), and D4
(unapproved egress of customer-like data). *Address:* implement them as **layered** detections so a miss
at one boundary is caught at the next; D3 in particular catches the deploy→data step even if the
credential grab looked normal.

**Detection.** It polls CloudTrail every 15 s, watches one role and one STS operation, and depends on a
GitHub API lookup using a reused operator credential. *Address:* move to **EventBridge → Lambda → SIEM**
(event-driven, needs an active trail), broaden to **all deploy-capable roles**, and issue a **dedicated
least-privilege `Actions: read` token** instead of reusing the operator's. Add automated response
(revoke the session, open a ticket) so detection shortens into containment.

**Prevention.** We fixed one role's trust policy by hand in IAM. *Address:* manage trust in Terraform
with a lint/policy check that rejects any `pull_request` subject, so the fix can't silently regress; and
prefer GitOps so CI holds no deploy credentials to steal in the first place.

**Validation.** Three live samples; no production false-positive rate or latency distribution.
*Address:* backtest months of real role-assumption events, build a labeled replay corpus, and report
p50/p95 TTD and a measured FP rate before anyone gets paged.

**Engineering handoff.** We have a channel message and this write-up. *Address:* pilot in monitor-only
mode to baseline alert volume, then socialize the main-only trust change with platform owners before
enforcing, with a named alert owner and triage path.

### Why this is a simplistic model

- The operator **authored the PR** — there's no real infostealer and no real AI agent; A1 is assumed.
- The EKS endpoint was made **CI-reachable (public, authenticated)** to keep the demo fully remote; a
  real Mybank cluster might be private, which changes the runner-to-cluster step.
- The dataset is **two invented customers**, and exfiltration is **printed to the log** rather than sent
  to a webhook — enough to prove data *read*, but not the full T1567.004 egress step.
- We proved the chain for **one role, one repo, one workflow**. Real environments have many roles, forks
  (which behave differently for OIDC), environment-scoped tokens, and private runners — none exercised.
- **SAML federation, the private runner, image publish, and live network enforcement** were set up in
  the lab but not all exercised for this demo; the recorded earlier run (private endpoint) proved only
  the credential-grab boundary, while the fully-remote run reaches data.
- Timing numbers come from **one polling collector**, so they include polling granularity and are
  observations, not service guarantees.

### What we'd do with more time

- **Layer all four detections** (D1–D4) and show a miss at one boundary caught at the next.
- **Productionize D2:** EventBridge-driven, into the SIEM, across every deploy-capable role, with
  automated session revocation and ticketing.
- **Enforce prevention in code:** Terraform-managed trust with a CI policy check that bans
  `pull_request` subjects, plus a GitOps deployment model so CI holds no standing deploy credentials.
- **Exercise the realistic variants:** forks, private cluster endpoint + private runner, environment
  tokens, and a real (owned) egress receiver to complete the exfiltration measurement.
- **Statistical validation:** months of backtest for a real FP rate and TTD distribution, plus a small
  red-team pass trying to evade the correlation (odd subject formats, timing, session names).
- **Harden the agent-token story:** short-lived, scoped tokens for AI agents, and detection for anomalous
  agent-token use at the GitHub layer (closing the gap that A1 currently just assumes).
