# Mybank D2 demo

Everything here is a **fictional bank with invented records in our own AWS sandbox** (`us-east-1`, N. Virginia). The story: a stolen AI-coding-agent token opens an unreviewed pull request; the PR's automated tests run the attacker's code and obtain the AWS identity that deploys the bank; the attacker uses it to read customer data. You then **build the detection live**, catch it, **build the prevention live**, and show the next attempt fail.

This one file is the whole thing: stand it up (Part A), prepare (Part B), present (Part C), tear down (Part D). On the day you mostly live in **Part C**.

## The identities in play (know these cold — you'll be asked)

| Identity | What it is | Who/what uses it | Can it read customer data? |
| --- | --- | --- | --- |
| **Your GitHub account** | the human | you — the developer in Beat 1, the attacker in Beat 2 | No. GitHub only; it can't touch AWS directly. |
| **`mybank-sandbox-d2-demo-deploy`** (AWS IAM role) | the *deployment identity*. In Kubernetes it maps to the group `mybank:deployers`, which is allowed to replace the app's Deployment | obtained by a **PR's CI job** by exchanging a GitHub OIDC token | Not directly — but it can **replace the app**, and the app can. |
| **`mybank-sandbox-app`** (EKS Pod Identity role) | the *app's own identity*. Allowed to read the customer tables (`GetItem`) | the running `mybank-api` pods | **Yes.** This is the access the attacker inherits by replacing the app. |
| **`demo-admin`** (+ the bootstrap role) | **you, the operator** running the demo and the tunnel | your terminal and the AWS console | Not part of the attack. |

The attack is a two-step privilege pivot: **GitHub write access → the deployment identity** (Beat 2), then **deployment identity → the app's data access** (Beat 3). When a step below says "the identity," it means `mybank-sandbox-d2-demo-deploy` / the `mybank:deployers` group.

## What the audience sees

| Phase | What you do | What they see |
| --- | --- | --- |
| 1. Legitimate change | A reviewed PR → merge → the trusted pipeline deploys it | PR checks green; new text live on the app |
| 2. Attack succeeds | Open an unreviewed PR; its CI obtains the deployment identity | CI output: identity obtained |
| 3. Impact | Use that identity to replace the app and read customer records | Pod logs: `acct-alice`/`acct-bob` + customer details |
| 4. Build detection (live) | Start the monitor you wrote; attack again | Monitor alerts `pr_role_misuse` in ~1 min — attack still gets in |
| 5. Build prevention (live) | Restrict the role's trust to `main`; attack again | `AccessDenied`; monitor shows `assumption_denied`; normal release still works |
| 6. Evidence | CloudTrail / the monitor | the signed grant and the blocked retry, from outside the attacker's control |

```text
Legitimate:  main ──► build role ──► ECR ──► deploy role ──► private runner (in VPC) ──► EKS ──► app ──► DynamoDB
Operator:    laptop ──► SSM (IAM, logged, no inbound ports) ──► private EKS API ──► port-forward ──► app (API key)
Attack:      stolen token ──► PR ──► hosted runner ──► deploy identity ──┬─► replace app ──► app identity ──► customer data
                                                                        └─► CloudTrail ──► independent monitor ──► ALERT
```

> **One honest line to say out loud.** The pivot is that an **unreviewed PR obtains the identity trusted to deploy the app**; from there it replaces the app and inherits its data access (Beat 3 shows real synthetic records). The detection fires at the **credential grab** — the earliest link. Honest caveat worth stating: a GitHub-hosted PR runner can't reach the private cluster, so the Beat 3 steps run from your in-VPC tunnel, representing an attacker whose pipeline deploys with cluster access (a common real pattern).

---

## Part A — Stand it up (~20–25 min, unattended)

From the repository root in PowerShell:

1. Sign the local CLI in as your console user (browser approval, no access keys):

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.login     # approve as demo-admin
   ```

2. Build everything:

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.up
   ```

   Review the Terraform summary, type `y`. Seven stages print `[ok]`: Terraform (private EKS, DynamoDB, IAM, ops host) → GitHub wiring (no secrets) → image to private ECR → private release runner → app bootstrap → synthetic data → one trusted `main` release. Idempotent: if a stage fails, fix it and re-run `up`.

3. (Optional) Look around the AWS console, region **N. Virginia**: **EKS → `mybank-sandbox` → Resources → Workloads** (`mybank` namespace), **DynamoDB → `mybank-sandbox-accounts` → Explore items**, **ECR → `mybank-sandbox/api`**, **IAM → Roles** (`mybank-sandbox-deploy` is `main`-only; `mybank-sandbox-d2-demo-deploy` is the exercise role the attack targets).

---

## Part B — Prepare to present (just before the panel)

Open **two terminals** at the repo root and **one GitHub tab** on the repo. (Optional: one AWS console tab as `demo-admin` in N. Virginia for Beat 6.)

**Terminal 1 — private app access.** Opens the SSM tunnel and points `kubectl` at the private cluster. Used in Beats 1 and 3. Paste the whole block, leave the window open:

```powershell
. ./scripts/aws/session.ps1
$o = Get-Content .cache/outputs.json -Raw | ConvertFrom-Json
Start-Process -FilePath (Get-Command aws).Source -ArgumentList @('ssm','start-session','--target',$o.operations_instance_id.value,'--document-name','AWS-StartPortForwardingSessionToRemoteHost','--parameters',"host=$($o.cluster_endpoint_hostname.value),portNumber=443,localPortNumber=8443") -WindowStyle Hidden
Start-Sleep 8
$env:KUBECONFIG = "$PWD\.cache\kubeconfig"
aws eks update-kubeconfig --name mybank-sandbox --role-arn arn:aws:iam::404824402451:role/mybank-sandbox-bootstrap --alias mybank | Out-Null
kubectl config set-cluster arn:aws:eks:us-east-1:404824402451:cluster/mybank-sandbox --server=https://127.0.0.1:8443 --tls-server-name=$($o.cluster_endpoint_hostname.value) | Out-Null
$key = Get-Content .cache/demo-api-key
Start-Process kubectl -ArgumentList '-n','mybank','port-forward','service/mybank-api','8080:8000' -WindowStyle Hidden
```

**Terminal 2 — leave it open and empty.** You start the monitor *in it, live*, during Beat 4. Just `. ./scripts/aws/session.ps1` in it now so it's ready.

**Confirm the vulnerable starting state** — prevention OFF, so the first attack succeeds. This makes sure the exercise role's trust currently accepts PR jobs (the misconfiguration under test):

```powershell
.venv/Scripts/python.exe -m scripts.demo.prevent off
```

Nothing is "watching" or "blocking" yet — that's deliberate. You add both controls live in Beats 4 and 5.

---

## Part C — Run the demo (~12 min)

### Beat 1 — the legitimate change (~40s, GitHub tab)

**You're doing:** playing a normal engineer shipping a reviewed change.

1. GitHub → **Code** → open `app/release.py` → click the **pencil (Edit)**.
2. Change the line to: `RELEASE_NOTE = "hello from the panel"`.
3. **Commit changes…** → **Create a new branch for this commit** (call it `release-note`) → **Propose changes** → **Create pull request**.
4. On the PR, open the **Checks** tab. The checks run on GitHub's own machines and go **green**.

> **Say:** *"Normal change. CI ran on GitHub-hosted machines with no access to AWS. A reviewer approves, it merges to `main`, and only then does the trusted pipeline deploy it."* Merge it if you want the green-tick and to see `/health` update later; not required.

**Technically:** PR checks have `contents: read` and no `id-token` permission for AWS — they cannot obtain AWS credentials. Deploys only happen from `main`, on a private runner.

### Beat 2 — the attacker obtains the deployment identity (~2 min, GitHub tab)

**You're doing:** acting as an attacker who phished a junior developer's AI-coding-agent GitHub token. You can't merge anything (no review rights), but you *can* open a PR — and PR tests run **before** anyone reviews them. Your goal is to make the PR's test job hand you AWS deployment access.

> **Say first (motivation):** *"I've stolen a coding agent's GitHub token. I can't approve or merge, but I can open a pull request, and this repo runs automated tests on PRs before review. I'm going to put my own code in one of those test scripts so it runs in CI — and see what AWS access that CI job can get."*

1. GitHub → **Code** → open `scripts/d2/demo_probe.py` → **pencil (Edit)**.
2. Change the line `MARKER = "original-harmless-probe"` to `MARKER = "owned-1"`. 

   > **Say:** *"This file stands in for any build or test script a PR runs. Editing it is how my code ends up executing in the pipeline. The script itself is deliberately harmless — it just reports which AWS identity the job can get."*
3. **Commit changes…** → **Create a new branch** (call it `agent-cleanup`) → **Propose changes** → title it something innocuous like `Tidy probe output` → **Create pull request**. **Do not merge it.**
4. On the PR → **Checks** → open **D2 identity-boundary exercise → identity-probe** → expand the **Execute … identity probe** step. Read the JSON out loud:
   - `obtained_identity: …assumed-role/mybank-sandbox-d2-demo-deploy/…` — **the unreviewed PR just obtained the deployment identity.**
   - `direct_database_read: blocked by IAM` and `reach_private_cluster: blocked by network` — that identity *by itself* can't read the database or reach the cluster from a hosted runner. The real move is to *use it to replace the app*, next.

> **Say:** *"A pull request nobody approved now holds the AWS identity trusted to deploy our banking backend. That's the breach."*

**Technically:** the CI job requested a GitHub OIDC token and called `sts:AssumeRoleWithWebIdentity`. AWS accepted it because the exercise role's trust policy currently allows the `pull_request` context — the misconfiguration we're demonstrating.

### Beat 3 — ride that identity to customer data (~2 min, Terminal 1)

**You're doing:** the post-grab steps. You now hold the deployment identity, so you replace the running app with your own container; because app pods run under the app's data-reading identity, your container inherits that access. This happens in **Terminal 1** (your tunnel), not GitHub.

> **Say (motivation + caveat):** *"Holding the deploy identity, I can't read the database directly — but I can replace the running app. The app's pods carry an identity that's allowed to read customer records, so my replacement inherits it. One caveat: a GitHub-hosted runner can't reach the private cluster, so I run these steps from an in-VPC position — exactly what an attacker gets in an org whose pipeline deploys with cluster access."*

**Easy path — one command.** It performs all four sub-steps and prints each:

```powershell
.venv/Scripts/python.exe -m scripts.demo.impact
```

Read the output as it prints:
- **Scope check** — `can-i patch deployment/mybank-api: yes`, `can-i get secret/mybank-api: no`. *Say: "This identity can replace the app but can't even read the app's API-key secret — it's scoped, yet still enough."*
- **"replace app container with a data reader"** — you (as the deploy identity) patched the Deployment.
- **`STOLEN SYNTHETIC CUSTOMER RECORDS:`** then `acct-alice`, `acct-bob`, and the two customers (names, emails, balances). *Say: "Deploy access just became customer-data access."*
- **"app restored"** — the real app is put back.

**Manual path (same four steps, if you prefer to run them by hand).** Each runs in Terminal 1:

1. Show the identity's scope (acting *as* the attacker's Kubernetes group via impersonation):
   ```powershell
   kubectl auth can-i patch deployment/mybank-api -n mybank --as mybank-deployer --as-group mybank:deployers   # yes
   kubectl auth can-i get secret/mybank-api    -n mybank --as mybank-deployer --as-group mybank:deployers        # no
   ```
   `--as … --as-group mybank:deployers` is **impersonation**: your operator session acts with *exactly* the permissions the stolen identity maps to — nothing more — so the panel sees the scoped identity is sufficient.
2. Write the malicious replacement container to a file, then apply it as the deploy identity (the `` ` `` is line-continuation; both lines are one command):
   ```powershell
   @'
   {"spec":{"template":{"spec":{"containers":[{"name":"api","command":["sh","-c","python -c 'import boto3,os,json; c=boto3.client(\"dynamodb\",region_name=os.environ.get(\"AWS_REGION\",\"us-east-1\")); print(\"SYNTHETIC CUSTOMER RECORDS:\"); [print(json.dumps(c.get_item(TableName=os.environ[\"ACCOUNTS_TABLE\"],Key={\"account_id\":{\"S\":a}}).get(\"Item\"))) for a in (\"acct-alice\",\"acct-bob\")]; [print(json.dumps(c.get_item(TableName=os.environ[\"CUSTOMERS_TABLE\"],Key={\"customer_id\":{\"S\":u}}).get(\"Item\"))) for u in (\"cust-alice\",\"cust-bob\")]'; sleep 3600"],"livenessProbe":null,"readinessProbe":null,"startupProbe":null}]}}}}
   '@ | Set-Content -Encoding utf8 .cache/hijack-patch.json

   kubectl -n mybank --as mybank-deployer --as-group mybank:deployers `
     patch deployment mybank-api --type strategic --patch-file .cache/hijack-patch.json
   ```
3. Wait for the replaced pod, then read what it harvested:
   ```powershell
   Start-Sleep 25
   kubectl -n mybank logs -l app.kubernetes.io/name=mybank-api --tail=20
   ```
4. Restore the real app (as the operator):
   ```powershell
   kubectl -n mybank rollout undo deployment/mybank-api
   kubectl -n mybank rollout status deployment/mybank-api
   ```

**At this point the attack has fully succeeded and nothing noticed.** That's the setup for building the controls.

### Beat 4 — build the detection, catch it live (~2 min, Terminal 2 + GitHub)

**You're doing:** turning on the thing you built for this assignment — an independent monitor that watches AWS's credential-issuance log and GitHub's run records, and alerts when a PR job obtains the deploy identity.

> **Say:** *"So far nothing caught that. Here's the detection I built. It runs outside GitHub — so a compromised PR can't disable it — and it correlates AWS's signed record of the credential grant with GitHub's own record of the job. Let me start it and attack again."*

1. (Optional, to show the artifact) point at the detector code: `scripts/d2/detector.py` (the decision logic) and `scripts/d2/collect.py` (reads CloudTrail + GitHub). Say one line: *"This is the rule — it classifies each credential grant as expected-release, PR-misuse, or denied."*
2. In **Terminal 2**, start the monitor:
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.watch --minutes 60 --lookback 1
   ```
   It prints that it's watching the exercise role and polling. Leave it visible.
3. Attack again — in GitHub, re-trigger the PR's tests with a fresh change: **Code** → switch to the **`agent-cleanup`** branch (branch dropdown) → open `scripts/d2/demo_probe.py` → **Edit** → change the marker to `MARKER = "owned-2"` → **Commit directly to the `agent-cleanup` branch**.
4. Watch **Terminal 2**. Within about a minute it prints:
   ```
   pull_request run <N> -> pr_role_misuse
       ALERT (high): Deployment credentials issued to PR validation
   ```

> **Say:** *"The attack still succeeded — detection isn't prevention — but now security sees it within about a minute, with the role, the run link, and the evidence. And it used AWS's signed subject and GitHub's run record, not the session name, which the attacker chose to look like a release."*

**Technically:** prevention is still off, so AWS still issues the credential; the monitor classifies the grant as `pr_role_misuse` because the GitHub context is a `pull_request` run, verified against GitHub's own API.

### Beat 5 — build the prevention, block the next attempt (~1 min, Terminal 1 + GitHub)

**You're doing:** applying the fix as infrastructure-as-code — removing the `pull_request` context from the exercise role's trust policy, so AWS refuses to hand the identity to PR jobs at all.

> **Say:** *"Detection is good, but let's close the door. I'll change the role's trust policy — as code — so it only trusts `main`, never pull requests."*

1. In **Terminal 1**, apply the control live:
   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent on
   ```
   It runs Terraform and prints `Apply complete!` and the remaining trusted contexts — only `main` push and manual dispatch, no `pull_request`. *Say: "That's a real IAM trust-policy change, in version control, reviewable like any other."* Wait ~30 seconds for IAM to propagate.
2. Attack a third time: GitHub → `agent-cleanup` branch → `scripts/d2/demo_probe.py` → **Edit** → `MARKER = "owned-3"` → **Commit directly to the `agent-cleanup` branch**.
3. On the PR → **Checks** → **identity-probe** now **fails**:
   ```
   AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity
   ```
   And **Terminal 2** prints `pull_request run <N> -> assumption_denied`.
4. (Optional) show legitimate releases still work: GitHub → **Actions → Main release → Run workflow → branch `main` → Run workflow** — it succeeds end to end.

> **Say:** *"Same attack, now refused by AWS before any credential is issued — and normal `main` releases still deploy. Detection tells us when something slips; this trust policy stops it."*

### Beat 6 — the evidence, from the source (~1 min, optional AWS console)

AWS console → **CloudTrail → Event history** → filter *Event name* = `AssumeRoleWithWebIdentity`. The successful event (resource `mybank-sandbox-d2-demo-deploy`) is the attack's grab; the newest event shows **error `AccessDenied`** — the blocked retry after you turned on prevention.

> **Say:** *"Same story at the source: AWS's own audit log shows the grant we detected, and the denial after the fix. The detector reads exactly this, plus GitHub's run record, from outside anything the attacker controls."*

**Demo over.** To reset for another run: `.venv/Scripts/python.exe -m scripts.demo.prevent off`, and close the `agent-cleanup` PR without merging.

---

## Part D — Tear it down

```powershell
.venv/Scripts/python.exe -m scripts.demo.down
```

Stops deployments, removes the runner registration, closes demo PRs without merging, destroys the lab, and verifies no EKS cluster, instance, NAT gateway or elastic IP remains. The Terraform state bucket, bootstrap role and budget alert are kept on purpose. At ~USD 0.35/hour you can also leave it up between rehearsals.

---

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| `ProfileNotFound`, `ExpiredToken`, sign-in error | `.venv/Scripts/python.exe -m scripts.demo.login`, then re-run `. ./scripts/aws/session.ps1` in the terminal |
| `Local port 8443 is busy` | A tunnel is already open; close the other window, or `taskkill /F /IM session-manager-plugin.exe`, then redo Terminal 1 |
| `curl`/`kubectl` hangs in Terminal 1 | The SSM tunnel timed out; re-run the Terminal 1 block |
| Monitor silent after an attack | CloudTrail takes a minute or two; wait. Confirm you started it before the attack (`--lookback 1` only sees new events) |
| `prevent on` then attack still succeeds | IAM needs ~30s to propagate; push the next marker change a moment later |
| PR check didn't start | The change must be to `scripts/d2/demo_probe.py` on a branch **in this repo** (not a fork) |
| `up` stops at a stage | Read the message, fix, re-run `up` (each stage is idempotent) |
| EKS console can't show workloads | Sign in as `demo-admin`, not root |

## Likely questions

| Question | Answer |
| --- | --- |
| Did the attacker get customer data? | Yes — Beat 3 shows synthetic records coming out, by using the deploy identity to replace the app and inherit its data access. The detection fires at the credential grab, before that stage. |
| Is the attacker a different GitHub user? | No — same account; what differs is the *action* (an unreviewed PR vs. a reviewed merge to `main`). The detector keys on the **context the credentials came from** (a `pull_request` run vs. a `main` run), not the username. |
| Could they hide by naming the session "release"? | No. The monitor uses GitHub's signed subject and run record, never the attacker-chosen session name. |
| Why detect if the trust change prevents it? | Defense in depth, and the detector is what *found* the gap. Networks and configs drift; the alert is the early warning. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy credentials; and scan Terraform for trust policies that admit `pull_request`. |

Recorded results: [docs/d2/evidence.md](docs/d2/evidence.md). Detection logic: [scripts/d2](scripts/d2/README.md). Infrastructure: [infra](infra/README.md).
