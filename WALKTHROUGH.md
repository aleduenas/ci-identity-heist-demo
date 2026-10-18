# Presenter walkthrough: legitimate change vs. stolen-agent PR

A click-by-click guide for performing the demo by hand in GitHub and the AWS console. The environment must already be up ([DEMO.md](DEMO.md) → *Stand it up*). Everything is synthetic, in AWS **`us-east-1` (N. Virginia)** and the private repository `aleduenas/mybank-eks-sandbox`.

**The story in one breath:** a reviewed change flows through the trusted pipeline into a private EKS app. Then an attacker with a stolen AI-coding-agent token opens an unreviewed PR. The PR's automated tests obtain a deploy-capable AWS identity, but can't read customer data or reach the cluster. Security's monitor catches the credential grant within about a minute, and one trust-policy change prevents it entirely.

---

## Part 0: Prepare (15 minutes before the panel)

### 0.1 Browser tabs

| Tab | Where |
| --- | --- |
| GitHub: Code | repository home |
| GitHub: Pull requests | `…/pulls` |
| GitHub: Actions | `…/actions` |
| GitHub: Runners | Settings → Actions → Runners |
| AWS: EKS | Console (signed in as **`demo-admin`**, region **N. Virginia**) → EKS → `mybank-sandbox` |
| AWS: CloudTrail | CloudTrail → **Event history** |
| AWS: IAM role | IAM → Roles → `mybank-sandbox-d2-demo-deploy` → **Trust relationships** |
| AWS: ECR | ECR → Private repositories → `mybank-sandbox/api` |
| AWS: DynamoDB | DynamoDB → Tables → `mybank-sandbox-accounts` → Explore table items |

### 0.2 Three PowerShell terminals, all at the repository root

**Terminal A: private tunnel to the cluster** (leave it open)

```powershell
.venv/Scripts/python.exe -m scripts.demo.login        # once; approve in the browser as demo-admin
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. ./scripts/aws/session.ps1
$o = Get-Content .cache/outputs.json -Raw | ConvertFrom-Json
aws ssm start-session --target $o.operations_instance_id.value --document-name AWS-StartPortForwardingSessionToRemoteHost --parameters "host=$($o.cluster_endpoint_hostname.value),portNumber=443,localPortNumber=8443"
```

You should see `Port 8443 opened … Waiting for connections...`.

> Talking point: this is AWS Systems Manager, authenticated by IAM and logged in CloudTrail. The operations host has **no inbound ports**, and the cluster API has **no public endpoint**.

**Terminal B: operator's kubectl and the app**

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
. ./scripts/aws/session.ps1
$o = Get-Content .cache/outputs.json -Raw | ConvertFrom-Json
$env:KUBECONFIG = "$PWD\.cache\kubeconfig"
aws eks update-kubeconfig --name mybank-sandbox --role-arn arn:aws:iam::404824402451:role/mybank-sandbox-bootstrap --alias mybank
kubectl config set-cluster arn:aws:eks:us-east-1:404824402451:cluster/mybank-sandbox --server=https://127.0.0.1:8443 --tls-server-name=$($o.cluster_endpoint_hostname.value)
kubectl -n mybank get deployment,pods,service
Start-Process kubectl -ArgumentList '-n','mybank','port-forward','service/mybank-api','8080:8000' -WindowStyle Hidden
$key = Get-Content .cache/demo-api-key
```

**Terminal C: security's monitor** (start it now; it watches for 90 minutes)

```powershell
.venv/Scripts/python.exe -m scripts.demo.watch --minutes 90
```

> Talking point: this is the **detection rule** being demonstrated. It runs outside GitHub, so the attacker's PR can't change it. It reads AWS CloudTrail plus GitHub's own run records.

### 0.3 Confirm the starting state

- GitHub → Runners: `mybank-sandbox-ops` is **Idle**.
- IAM role → Trust relationships: three `sub` patterns, including one with `pull_request` (detection mode). If it's missing, run `.venv/Scripts/python.exe -m scripts.demo.prevent off`.
- No open PRs.

---

## Part 1: Show the running app (2 minutes)

In **Terminal B**:

```powershell
curl.exe http://127.0.0.1:8080/health
curl.exe http://127.0.0.1:8080/accounts/acct-alice
curl.exe -H "X-API-Key: $key" http://127.0.0.1:8080/accounts/acct-alice
```

Expected output:
1. `{"status":"ok","release_note":"initial release"}`
2. `{"detail":"Valid X-API-Key required"}`, because the app refuses without its key
3. `{"account_id":"acct-alice",…,"balance_cents":100000}`, one customer's record

Then show:
- **DynamoDB tab:** the same `acct-alice` record in the table.
- **EKS tab → Resources → Workloads → Deployments → `mybank-api`:** two pods in namespace `mybank`. Under the cluster's **Networking** tab, API server endpoint access is **Private**.

> Talking point: to read that record you need IAM (SSM), Kubernetes RBAC (port-forward) **and** the app's API key, all over a private path. Only the app itself has database permission, through its own Pod Identity role.

---

## Part 2: The legitimate change (about 8 minutes)

### Step 1: An engineer opens a PR

1. GitHub → **Code** → open `app/release.py` → click the **pencil (Edit)** icon.
2. Change `RELEASE_NOTE = "initial release"` to `RELEASE_NOTE = "reviewed change for the panel"`.
3. **Commit changes…** → choose **Create a new branch for this commit and start a pull request**, with branch name `release-note-update` → **Propose changes** → **Create pull request**.

### Step 2: Watch the PR checks (and what they're *not* given)

1. On the PR, open the **Checks** tab. **Pull request checks** runs `checks / application`, `checks / infrastructure` and `checks / kubernetes` on GitHub-hosted machines.
2. Open `checks / application` → *Set up job*: the runner is **GitHub Actions** (hosted). Its token permissions are `Contents: read`. It **can't request AWS credentials**.
3. **D2 identity-boundary exercise** does **not** appear, because this PR doesn't touch the PR-executed probe.

### Step 3: Review and merge

1. **Files changed** tab: one line. In a real team a second engineer approves here (you can't approve your own PR; say so).
2. **Merge pull request** → **Confirm merge**.

### Step 4: Trace the trusted release

GitHub → **Actions** → **Main release** → the newest run (event `push`, your merge commit). Open each job in order:

| Job | Open this step | What it proves |
| --- | --- | --- |
| `checks / …` | any | Same tests as the PR, re-run on `main` |
| `verify-identity` | *Verify immutable OIDC subject…* | Shows the GitHub identity `sub`: `repo:aleduenas@…/mybank-eks-sandbox@…:ref:refs/heads/main:event_name:push:run_id:<RUN>:run_attempt:1`. Only `main` push/dispatch matches the AWS trust |
| `publish` | *Run aws-actions/configure-aws-credentials* | `Authenticated as assumedRoleId …:mybank-build-<RUN>`: the build role, no stored keys |
| `publish` | *Publish commit image…* | Image pushed to private ECR, tagged with the commit SHA |
| `deploy` | *Set up job* | Runner name **`mybank-sandbox-ops`**: the private host inside the VPC |
| `deploy` | *Run aws-actions/configure-aws-credentials* | `…:mybank-deploy-<RUN>`: the **deploy role**, which trusts `main` only |
| `deploy` | *Update only the application image* | `kubectl` rollout of the new image digest |

While `deploy` runs, the **Runners** tab shows `mybank-sandbox-ops` as **Active**.

### Step 5: Follow it in AWS

1. **CloudTrail → Event history:** set the filter to *Event name* = `AssumeRoleWithWebIdentity`. The two newest events are the build and deploy roles. Open the **deploy** one → **Event record** → `responseElements.subjectFromWebIdentityToken`. It ends with `event_name:push:run_id:<RUN>`, the **same run ID** as the GitHub run.

   > AWS itself records exactly which GitHub run received the deployment role.
2. **ECR tab:** refresh. A new image tag equals the merge commit SHA.
3. **EKS tab → Deployments → `mybank-api`:** two pods only a minute or two old. In **Terminal B**:

   ```powershell
   kubectl -n mybank get pods
   kubectl -n mybank get deployment mybank-api -o "jsonpath={.spec.template.spec.containers[0].image}"
   ```

   The digest matches the image the release published.

### Step 6: The change is live

**Terminal B:** `curl.exe http://127.0.0.1:8080/health` → `"release_note":"reviewed change for the panel"`.

> Talking point: a reviewed change reached production only through `main`, the main-only deploy role and the private runner.

### Step 7 (optional): The same exercise role, used legitimately, raises no alert

GitHub → Actions → **D2 identity-boundary exercise** → **Run workflow** → branch `main` → **Run workflow**. About a minute later, **Terminal C** prints `workflow_dispatch run … -> expected_release`, with no alert.

> Talking point: the monitor doesn't alert on the role; it alerts on the **wrong context**.

---

## Part 3: The stolen-agent PR (about 10 minutes)

### Set the scene (say this first)

- The attacker stole a junior developer's AI coding-agent token. It can push branches and open PRs, but **can't merge** without review.
- PR checks run automatically **before** review.
- The exercise role `mybank-sandbox-d2-demo-deploy` is a copy of the deploy role that is **deliberately misconfigured** to also trust PR jobs. That's the realistic mistake under test. The real deploy role stays main-only.
- `scripts/d2/demo_probe.py` stands in for "a test script the PR runs". For safety it is pre-instrumented with a **harmless** probe: request the role, try one database read, try to reach the cluster. It changes nothing. Editing that file is what makes the PR test run it.
- You play the compromised agent using your own GitHub account. The point is that the account only has ordinary write access.

### Step 1: The agent opens an innocent-looking PR

1. GitHub → **Code** → `scripts/d2/demo_probe.py`. Briefly show `main()`, `try_database` and `try_cluster`.
2. Click **Edit**. Change `MARKER = "original-harmless-probe"` to `MARKER = "agent-cleanup"`.
3. **Commit changes…** → **Create a new branch…** named `agent-cleanup` → **Propose changes**. Title the PR `Tidy probe output` → **Create pull request**. **Don't merge it.**

### Step 2: The PR's test job runs the attacker's code

1. PR → **Checks**. **D2 identity-boundary exercise / identity-probe** starts on a **GitHub-hosted** runner, before anyone has reviewed the PR.
2. Open it → step *Execute harmless PR-editable identity probe*. The JSON output shows:
   - `"obtained_identity": "…assumed-role/mybank-sandbox-d2-demo-deploy/release-looking-demo"`. **The unreviewed PR got deploy-capable credentials.** Note the session name was chosen to look like a release.
   - `"direct_database_read": "blocked by IAM: AccessDeniedException"`. The deploy identity has no data permission.
   - `"reach_private_cluster": "blocked by network: private endpoint unreachable from runner …"`. It can't even reach the cluster to try a deployment.
3. Show what **didn't** happen:
   - **Actions:** no **Main release** run started.
   - **Runners:** `mybank-sandbox-ops` stayed **Idle**. PR code never runs on the private runner.

### Step 3: Security catches it

**Terminal C**, within about 1–2 minutes:

```text
[<time>] pull_request run <RUN> -> pr_role_misuse
    ALERT (high): Deployment credentials issued to PR validation
    AWS issued …mybank-sandbox-d2-demo-deploy at <time> to GitHub run <RUN> attempt 1, independently identified as pull_request validation.
    where: {'run_url': '…/actions/runs/<RUN>', 'cloudtrail_event_id': '…'}
```

Read it out: what happened, which role, which run, and where to look.

### Step 4: Verify the alert by hand (so it isn't magic)

1. **CloudTrail → Event history**, filter `AssumeRoleWithWebIdentity`. Open the newest event and check **Event record** → `requestParameters.roleArn` is `…/mybank-sandbox-d2-demo-deploy`. Then look at:
   - `subjectFromWebIdentityToken` ends in `pull_request:event_name:pull_request:run_id:<RUN>`. This was signed by GitHub and accepted by AWS.
   - `assumedRoleUser.arn` ends in `release-looking-demo`. That name was the attacker's choice, and the monitor ignores it.
2. Compare `<RUN>` with the run ID in the PR check's URL (`…/actions/runs/<RUN>/job/…`). They're the same run.
3. Optional: filter CloudTrail by *Event name* `DescribeCluster` to see the probe looking up the cluster endpoint, its reconnaissance step.

> Talking point: the alert joins two independent records, AWS's signed credential grant and GitHub's run record, both outside the attacker's control.

### Step 5: Prevention, one trust-policy change

1. **IAM tab → Trust relationships:** point at the `pull_request` pattern.
2. **Terminal B:**

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent on
   ```

   This is a Terraform change, the same infrastructure-as-code that built the lab. It prints `Apply complete! … 1 changed` and lists only the two `main` patterns.
3. Refresh **Trust relationships**: the `pull_request` line is gone. Wait about 30 seconds for IAM to propagate.

### Step 6: The agent tries again and AWS refuses

1. GitHub → **Code** → switch to branch **`agent-cleanup`** → `scripts/d2/demo_probe.py` → **Edit**. Change the marker to `agent-cleanup-2` → **Commit directly to the `agent-cleanup` branch**.
2. PR → **Checks**: `identity-probe` **fails**. The log shows `AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity`.
3. **Terminal C:** `pull_request run <RUN2> -> assumption_denied`.
4. **CloudTrail:** the newest `AssumeRoleWithWebIdentity` event has **Error code `AccessDenied`**, and its *User name* is the PR's subject.

### Step 7: Legitimate releases still work

GitHub → Actions → **Main release** → **Run workflow** on `main`. Every job succeeds, including `deploy`.

### Step 8: Close out

1. On the PR: **Close pull request** (don't merge) → **Delete branch**.
2. Reset for the next run: `.venv/Scripts/python.exe -m scripts.demo.prevent off`.

---

## Quick answers for likely questions

| Question | Answer |
| --- | --- |
| Why didn't the attacker deploy? | The cluster API is private and PR jobs run on GitHub-hosted machines outside the VPC. Only the main-only private runner can reach it. |
| Why not read the database with the role? | The deploy identity has no DynamoDB permission; only the app's own Pod Identity role does. |
| If it's blocked anyway, why detect? | Defense in depth: networks and runners change. A deploy-capable credential reaching PR code is the earliest signal that the boundary failed. |
| Could the attacker hide by naming the session "release"? | No. The monitor uses GitHub's signed subject plus GitHub's own run record, never the session name. |
| How fast? | Observed about 1 minute from AWS event to alert, including CloudTrail delivery and 15-second polling. |
| What's the real fix? | Trust deploy roles only from protected `main` (shown live). Better still: GitOps, so CI holds no deploy credentials at all. Also scan Terraform for trust policies that admit `pull_request`. |

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| Terminal A closed or `curl` hangs | SSM sessions time out when idle. Re-run the `aws ssm start-session` line in Terminal A, then the `Start-Process kubectl … port-forward` line |
| `ExpiredToken` or a sign-in error | `.venv/Scripts/python.exe -m scripts.demo.login`, then re-dot-source `session.ps1` |
| Monitor silent after the PR | CloudTrail can take a few minutes. Leave it running; confirm the event in Event history |
| PR check didn't start | The PR must change `scripts/d2/demo_probe.py` and come from a branch in this repository |
| EKS console can't show workloads | Sign in as `demo-admin`, not root |
