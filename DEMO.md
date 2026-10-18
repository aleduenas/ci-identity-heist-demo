# Mybank detection demo

**What this shows and why it matters.** Mybank ships code through GitHub → CI/CD → a Kubernetes (EKS) cluster. An attacker who steals a developer's AI-coding-agent GitHub token can't merge code, but can open a pull request — and the automated tests on that PR run *before* anyone reviews them. This demo shows, entirely from GitHub, that those PR tests grab the AWS identity used to deploy the app and use it to **read customer records**. Then it shows the two things I built: a **detection** that catches the credential grab within about a minute, and a **prevention** (an IAM trust-policy change) that stops it. Everything is a fictional bank with invented records in my own AWS sandbox. Terraform is used only to *build* the sandbox; the attack, the detection, and the fix are all GitHub + the AWS API, matching the given architecture.

**The identities (so the steps make sense):**
- **Your GitHub account** — the human. The developer in Step 1, the attacker in Step 2. Only touches GitHub.
- **`mybank-sandbox-detection-demo-deploy`** — the AWS *deployment* role. A PR's CI job can obtain it via GitHub OIDC. In Kubernetes it maps to the group `mybank:deployers`, which can replace the app. This is "the identity" the attack steals.
- **`mybank-sandbox-app`** — the *app's own* identity; it can read the customer tables. The attacker inherits it by replacing the app.
- **`demo-admin`** — you, the operator/defender. Used only to run the detection and apply the fix — never in the attack.

**Whose machine is whose:** the **attacker only uses the GitHub website**; their compute is the GitHub-hosted CI runner they drive through the PR. They never touch your repo or AWS. The **terminal you open is the defender's** — you use it to run the monitor and apply the IAM fix. The attack and the data theft happen entirely in GitHub Actions.

## What the audience sees

| Step | What you do | What they see |
| --- | --- | --- |
| 1. Legitimate change | Edit the probe's `CHECK_NOTE` (attack still commented) → PR → checks pass | PR checks green; no AWS touched |
| 2. Attack reaches data | Uncomment the attack in an unreviewed PR | Its CI job obtains the deploy identity, replaces the app, and prints `acct-alice`/`acct-bob` + customer records **in the Actions log** |
| 3. Build detection (live) | Start the monitor; attack again | Monitor alerts `pr_role_misuse` in ~1 min — attack still succeeds |
| 4. Build prevention (live) | Fix the role's trust in IAM; attack again | `AccessDenied` before any credential is issued; normal release still works |

```text
Attack (all in GitHub Actions):
  stolen token ─► PR ─► CI job ─► grab deploy identity ─► kubectl replace app ─► app identity ─► read customer data ─► printed in the run log
                                        └─► CloudTrail ─► your monitor ─► ALERT
Operator (your terminal): run the monitor; apply the IAM trust fix.
```

---

## Part A — Stand it up (~20–25 min, unattended)

From the repository root in PowerShell. For a fresh checkout, install the development dependencies, configure the state backend using [deployment setup](docs/deployment.md), and copy `infra/environments/sandbox/demo.tfvars.json.example` to ignored `.cache/sandbox.tfvars.json` with your account and bootstrap role. Keep `cluster_public_access=true` for this hosted-runner attack. Local tool/session setup is in [scripts/aws](scripts/aws/README.md).

1. Sign in (browser; approve as **`demo-admin`**). Fixes any `profile demo-admin could not be found` error:
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.login
   ```
2. Build the lab (EKS with a CI-reachable endpoint, DynamoDB, IAM, the app, data, a trusted release):
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.up
   ```
   Review the Terraform summary, type `y`. Seven stages print `[ok]`. Idempotent: if a stage fails, fix it and re-run.
3. Put the exercise role in its vulnerable state (trusts PR jobs) so the first attack succeeds — this edits the role's trust policy **directly in AWS IAM**, no Terraform:
   ```powershell
   . ./scripts/aws/session.ps1
   .venv/Scripts/python.exe -m scripts.detection.set_trust allow-pr
   ```

Keep one browser tab on the GitHub repo. Optional: an AWS console tab as `demo-admin`, region **N. Virginia (us-east-1)**, for CloudTrail / IAM.

---

# Demo

Four steps: a normal deploy, the attacker reaching customer data through the PR pipeline, building the detection, then the fix that blocks it.

## Step 1 — Legitimate action (a normal change to the very script the attacker abuses)

Engineers edit this probe script all day: change a value, open a PR, its checks run on GitHub's machines, it's reviewed, merged. In the shipped file the whole attack is **commented out**, so a normal change runs in CI and does nothing but a harmless status check — the *same file* the attacker weaponises in Step 2.

**Steps to follow:**
1. GitHub → **Code** → `scripts/detection/demo_probe.py` → **pencil (Edit)**.
2. Change `CHECK_NOTE = "ok"` to `CHECK_NOTE = "ok-v2"` (any value). Leave the commented `# === ATTACK PAYLOAD …` block at the bottom untouched.
3. **Commit changes…** → **Create a new branch** (`probe-note`) → **Propose changes** → **Create pull request**.
4. On the PR → **Checks** → the probe runs and prints only `{"check_note": "ok-v2", "status": "ok", …}` — **green**, and **no AWS was touched**.
5. (Optional) Merge to show it land on `main`.

> Say: *"A normal change to the exact script the attacker will use — but the attack line is commented out, so all CI does is a harmless status check. This job could ask AWS for the deploy identity; nothing in this change does. The vulnerability is sitting right here — a legitimate change just doesn't exploit it."*

## Step 2 — Attacker opens a PR and reaches customer data

You're the attacker. You phished a junior developer's AI-coding-agent GitHub token. You can't approve or merge — but you can open a PR, and this repo runs tests on PRs before review. The exploit already sits in that same script (`demo_probe.py`), pre-written in a `run_attack()` block that ships **entirely commented out** — a stand-in for code an attacker authored. You unleash it, and the PR's automated tests run it before anyone reviews.

**Steps to follow:**
1. GitHub → **Code** → `scripts/detection/demo_probe.py` → **pencil (Edit)**.
2. Comment out the two `smoke_check()` entrypoint lines (`if __name__ == "__main__":` / `    smoke_check()`), then uncomment the whole `# === ATTACK PAYLOAD …` block at the bottom — select it and press **Ctrl+/**. (Talk track: *"A real attacker writes this payload; here it's already in the file, commented out. I'm just uncommenting it."*)
3. **Commit changes…** → **Create a new branch** (`agent-cleanup`) → **Propose changes** → title `Tidy probe output` → **Create pull request**. **Do not merge.**
4. On the PR → **Checks** → open **detection identity-boundary exercise → identity-probe** → expand the run step. Read the log aloud:
   - `obtained_identity: …mybank-sandbox-detection-demo-deploy…` — the unreviewed PR got the deploy identity.
   - `Replaced mybank-api with a reader of the customer tables…`
   - `STOLEN CUSTOMER RECORDS:` followed by `acct-alice`, `acct-bob`, and the two customers (names, emails, balances).
   - `Restored the legitimate app.`

> Say: *"A pull request nobody approved just read our customers' financial records — names, emails, balances — straight out of the pipeline, on GitHub's runners."*

**Technical explanation.** Editing `demo_probe.py` is how attacker code runs in CI (it stands in for any build/test script a PR triggers). The job asks GitHub for an OIDC token and calls AWS `sts:AssumeRoleWithWebIdentity`; the deploy role's trust policy currently accepts the `pull_request` context, so AWS issues real deployment credentials. With those, the job runs `aws eks update-kubeconfig` against the cluster's API and `kubectl patch`es the `mybank-api` Deployment so its container reads the customer tables. Because the pod keeps the `mybank-api` service account, the replacement **inherits that account's Pod Identity role**, which is allowed to read the tables — the privilege pivot from *deploy* to *data*. The job prints what it read and rolls the app back. In Step 1 the same probe ran in CI, but the attack block was commented out, so it never requested any AWS credentials — the job *could* have (the vulnerability is real and sitting in this pipeline), but a legitimate change simply doesn't exercise it. That is the whole point: exposure exists; only an explicit attack turns it into data loss.

## Step 3 — Build the detection and catch it

Nothing above noticed. The detection I built reads AWS's own credential-issuance log — CloudTrail's always-on event history, via the AWS API — correlates it with GitHub's run records, and alerts when a *PR* job obtains the deploy identity. It runs outside GitHub, so a compromised PR can't disable it.

**Steps to follow:**
1. (Show the work) Open `scripts/detection/detector.py` (the rule) and `scripts/detection/collect.py` (reads CloudTrail + GitHub).
2. In your defender terminal, start the monitor (loads your read-only GitHub token and runs the detector against the live logs):
   ```powershell
   . ./scripts/aws/session.ps1
   .venv/Scripts/python.exe -m scripts.demo.watch --minutes 60 --lookback 1
   ```
3. Attack again (the attack block is already uncommented on this branch): GitHub → `agent-cleanup` branch → `scripts/detection/demo_probe.py` → **Edit** → bump `CHECK_NOTE` to `"owned-2"` → **Commit directly to the `agent-cleanup` branch**. (Changing `CHECK_NOTE` just triggers a fresh run; the attack block stays uncommented.)
4. Within ~1 minute the monitor prints:
   ```
   pull_request run <N> -> pr_role_misuse
       ALERT (high): Deployment credentials issued to PR validation
   ```

> Say: *"The attack still succeeded — detection isn't prevention — but now security sees it within about a minute, with the role, the run link, and the evidence. It correlates the AWS-recorded GitHub-signed subject with GitHub's own run record; it ignores the attacker-chosen session name."*

## Step 4 — Build the prevention and block it

Now the fix, applied directly in AWS: tighten the deploy role's trust policy so it only trusts `main`, never pull requests. The next PR attempt is refused by AWS before any credential is issued.

**Steps to follow (defender terminal):**
1. Show the current trust — note the `pull_request` line:
   ```powershell
   .venv/Scripts/python.exe -m scripts.detection.set_trust show
   ```
   (Wraps `aws iam get-role … --query Role.AssumeRolePolicyDocument`.)
2. Apply the fix — remove PR trust, keep `main`:
   ```powershell
   .venv/Scripts/python.exe -m scripts.detection.set_trust block-pr
   ```
   It calls `aws iam update-assume-role-policy` and prints the remaining `main`-only contexts. (AWS console: IAM → Roles → `mybank-sandbox-detection-demo-deploy` → **Trust relationships** → refresh; the `pull_request` line is gone.) Wait ~30 seconds for IAM to propagate.
3. Attack again (still uncommented): GitHub → `agent-cleanup` branch → `scripts/detection/demo_probe.py` → **Edit** → bump `CHECK_NOTE` to `"owned-3"` → **Commit directly to the `agent-cleanup` branch**.
4. On the PR → **Checks** → **identity-probe** now **fails**: `AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity`. The monitor prints `pull_request run <N> -> assumption_denied`. No app change, no data.
5. (Optional) Prove normal deploys still work: GitHub → **Actions → Main release → Run workflow → `main`** — it succeeds.

> Say: *"Same attack, refused by AWS before any credential exists — and normal `main` releases still deploy. Detection tells us when something slips; this trust policy stops it."*

**Technical explanation.** `set_trust block-pr` reads the role's live trust policy with the IAM API, drops the `pull_request` subject from its `StringLike` condition, and writes it back with `UpdateAssumeRolePolicy`. The PR job's `pull_request` subject no longer matches any allowed pattern, so `AssumeRoleWithWebIdentity` is denied — the job never gets credentials, so it can't reach the cluster or the data. The `main` patterns are untouched, so releases are unaffected.

**Reset after the demo:** `.venv/Scripts/python.exe -m scripts.detection.set_trust allow-pr`, close the `agent-cleanup` PR without merging, and Ctrl+C the monitor. The attack was uncommented only on that throwaway branch, so `main` keeps the attack block commented — nothing to revert there.

---

## Part D — Tear it down

```powershell
.venv/Scripts/python.exe -m scripts.demo.down
```
Removes the runner, closes demo PRs, destroys the lab, and verifies no EKS cluster, instance, NAT gateway or elastic IP remains. State bucket, bootstrap role and budget alert are kept on purpose. Nonempty ECR and audit storage resist deletion by default; archive or explicitly empty only the lab's retained data and resume the same destroy, as described in [teardown](docs/teardown.md). Retained storage can still incur charges; see [cost guidance](docs/infrastructure.md).

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| `config profile (demo-admin) could not be found` / `ExpiredToken` | `.venv/Scripts/python.exe -m scripts.demo.login`, then re-run `. ./scripts/aws/session.ps1` |
| `set_trust` says `Unable to locate credentials` | Dot-source `. ./scripts/aws/session.ps1` first (it needs your AWS session) |
| Monitor silent after an attack | CloudTrail takes a minute or two; wait. Make sure it was started before the attack |
| `set_trust block-pr` then attack still succeeds | IAM needs ~30s to propagate; push the next marker change a moment later |
| PR check didn't start | The change must be to `scripts/detection/demo_probe.py` on a branch in this repo (not a fork) |
| EKS console can't show workloads | Sign in as `demo-admin`, not root |

## Likely questions

| Question | Answer |
| --- | --- |
| Did the attacker get customer data? | Yes — Step 2 reads `acct-alice`/`acct-bob` and the customers, printed in the PR's CI log, all remotely. Detection fires at the credential grab, the earliest point. |
| Is the attacker a different GitHub user? | No — same account; what differs is the *action* (unreviewed PR vs. reviewed merge to `main`). The detector keys on the credential's **context** (`pull_request` vs `main` run), not the username. |
| How did the PR runner reach a private cluster? | The cluster API is reachable from CI (a public, IAM/RBAC-authenticated endpoint — common where pipelines deploy from GitHub). The vulnerability isn't the endpoint; it's PR jobs being able to obtain deploy credentials. |
| Could they hide with a "release"-looking session name? | No. The monitor uses GitHub's signed subject and run record, never the session name. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy credentials; and scan IAM/Terraform for trust policies that admit `pull_request`. |

Recorded results: [docs/detection/evidence.md](docs/detection/evidence.md). Detection + control code: [scripts/detection](scripts/detection/README.md). Infrastructure: [infra](infra/README.md).
