# Presenter walkthrough

Four beats. Almost everything happens in **one GitHub tab**. You only glance elsewhere at the very end.

- **Beat 1** — a legitimate PR. CI goes green, ready to merge.
- **Beat 2** — the attacker. Use the stolen agent's access to open a malicious PR and show it obtains the keys to deploy the bank.
- **Beat 3** — turn on the control, attack again, get stopped.
- **Beat 4** — show the evidence: the alert and the AWS record.

> **The one honest framing to say out loud.** The attack's win is that an **unreviewed PR obtains the AWS identity that can replace the running bank app**. That identity is the keys to the kingdom: whoever holds it can ship a modified app that reads customer data. In this sandbox the PR job does a *harmless* proof — it shows which identity it got — and deliberately stops there. It does not dump customer data on screen, and that's the point of this detection: **catch the credential grab at the moment it happens, before any data is touched.**

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
   - `direct_database_read: blocked by IAM` and `reach_private_cluster: blocked by network` — proof the identity alone can't read data yet; the attacker's path is to *use it to deploy a modified app*. The lab stops here, harmlessly.

Say: *"A PR that nobody approved now holds the identity trusted to deploy our banking backend. That's the vulnerability."*

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
| Did the attacker get customer data? | Not in the lab — it stops at proving the identity grab. That identity is what *would* let them deploy a data-stealing app; we detect/deny it before that. |
| Could they hide by naming the session "release"? | No. The monitor uses GitHub's signed subject and run record, never the attacker-chosen session name. |
| Why detect if the trust change prevents it? | Defense in depth, and the detector found the gap in the first place. Networks and configs drift; the alert is the early warning. |
| Real-world fix? | Trust deploy roles only from protected `main` (shown live); better, GitOps so CI holds no deploy creds; and scan Terraform for trust policies that admit `pull_request`. |
