# Mybank D2 demo runbook

A stolen AI-coding-agent token is used to push an unreviewed pull request. The PR's automated tests run attacker-controlled code, and that code tries to obtain the AWS identity allowed to deploy the banking app. This demo shows the legitimate release path working, then the attack being **detected**, **contained** and finally **prevented**.

Everything is synthetic and lives in one AWS account in **`us-east-1` (N. Virginia)**.

## What the audience sees

| Act | What happens | Proof on screen |
| --- | --- | --- |
| 1. Normal operations | Reviewed code on `main` is built and deployed by the trusted pipeline; an operator reads one account privately | GitHub release run; EKS workloads; `acct-alice` balance via the private tunnel |
| 2. The attack | An unreviewed PR's test job obtains the deploy-capable role | PR check output: identity obtained |
| 3. Containment | That identity still cannot read customer data or reach the private cluster | Probe output: database read **denied by IAM**, cluster **unreachable** |
| 4. Detection | Security's independent watcher raises an alert within about a minute | `watch` terminal: `ALERT (high): Deployment credentials issued to PR validation` |
| 5. Prevention | Trust is restricted to `main`; the same attack is refused by AWS | PR check fails with `AccessDenied`; watcher shows `assumption_denied`; main releases still work |

```text
Legitimate:  main ──► build role ──► ECR ──► deploy role ──► private runner (in VPC) ──► EKS ──► app ──► DynamoDB
Operator:    laptop ──► SSM (IAM, logged, no inbound ports) ──► private EKS API ──► port-forward ──► app (API key)
Attack:      stolen token ──► PR ──► hosted runner ──► (detection mode) deploy-capable role
                                         ├─► DynamoDB read ✗ IAM          ├─► private EKS ✗ network
                                         └─► CloudTrail ──► independent watcher ──► ALERT
```

## Before you start (once per machine)

All commands run from the repository root in PowerShell, using the prepared virtual environment.

```powershell
.venv/Scripts/python.exe -m scripts.demo.login
```

A browser opens; approve the sign-in as **`demo-admin`**. The CLI then uses temporary credentials, with no access keys anywhere. Re-run this command whenever a later command reports expired credentials.

## Stand it up (about 20–25 minutes, unattended)

```powershell
.venv/Scripts/python.exe -m scripts.demo.up
```

Review the Terraform summary and type `y`. The script then runs seven stages and prints `[ok]` for each:

1. Terraform: private EKS cluster (no public endpoint), nodes, DynamoDB tables, IAM roles, operations host.
2. GitHub: OIDC subject template and repository variables (no secrets are stored in GitHub).
3. Image: the trusted `main` release builds the app and pushes it to private ECR.
4. Runner: registers the main-only release runner on the private operations host.
5. Kubernetes: bootstraps the `mybank` namespace and app with a fresh lab API key.
6. Data: seeds synthetic customers and accounts.
7. Release: a normal `main` release deploys through the deploy role on the private runner.

Every stage is safe to re-run. If one fails, fix the cause and run `up` again.

### Look around the AWS console (region **N. Virginia**)

- **EKS → `mybank-sandbox` → Resources → Workloads**, namespace `mybank`: the `mybank-api` deployment. Networking shows the API endpoint is private only.
- **DynamoDB → Tables → `mybank-sandbox-accounts` → Explore items**: `acct-alice`, `acct-bob`.
- **ECR → `mybank-sandbox/api`**: the image published by the release pipeline.
- **IAM → Roles**: `mybank-sandbox-deploy` (real releases, `main` only) and `mybank-sandbox-d2-demo-deploy` (the exercise role the attack targets).
- **CloudTrail → Event history**, filter *Event name* `AssumeRoleWithWebIdentity`: every credential issuance.

## Run the demo (about 10 minutes)

**Presenting live? Use [WALKTHROUGH.md](WALKTHROUGH.md)** — four beats, mostly one GitHub tab. The commands below are the quick scripted version for rehearsals.

Use two terminals.

**Terminal 1: security's watcher.** Start it first and leave it running.

```powershell
.venv/Scripts/python.exe -m scripts.demo.watch
```

**Terminal 2: the story.**

1. **Legitimate access to the app**

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.app
   ```

   This shows the running pods, a request **without** the API key (`401`), then `acct-alice` and `acct-bob` read through the private path. Talking point: no public endpoint exists; access needs IAM + SSM + Kubernetes RBAC + the app's key.

2. **The attack (detection mode)**

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.attack
   ```

   It opens an unreviewed PR (the "stolen agent" push) and prints the probe's findings from the PR's test job:
   - `obtained_identity` … `mybank-sandbox-d2-demo-deploy`: the PR job got deploy-capable credentials.
   - `direct_database_read`: **blocked by IAM**. The deploy identity can't read customer data directly.
   - `reach_private_cluster`: **blocked by network**. The hosted runner can't reach the private EKS endpoint.

   Within about a minute, terminal 1 prints `ALERT (high): Deployment credentials issued to PR validation`, with the run link. Talking point: the alert relies on AWS's signed record and GitHub's own run record, not on anything the PR could fake; the session name was deliberately made to look like a release.

3. **Prevention**

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent on
   .venv/Scripts/python.exe -m scripts.demo.attack --again
   ```

   The PR job now fails with `AccessDenied`, and terminal 1 shows `assumption_denied`. Optional: show a normal release still working by dispatching **Actions → Main release → Run workflow** on `main`.

4. **Reset for another run**

   ```powershell
   .venv/Scripts/python.exe -m scripts.demo.prevent off
   ```

## Tear it down

```powershell
.venv/Scripts/python.exe -m scripts.demo.down
```

This stops deployments, removes the runner registration, closes demo PRs without merging, destroys the lab and verifies that no EKS cluster, instance, NAT gateway or elastic IP remains. The Terraform state bucket, bootstrap role and budget alert are kept on purpose.

## If something goes wrong

| Symptom | Fix |
| --- | --- |
| `ProfileNotFound`, `ExpiredToken` or a sign-in error | Run `scripts.demo.login` again |
| Watcher shows nothing after the attack | CloudTrail can take a few minutes; leave it running. Check *Event history* in **N. Virginia** |
| `Local port 8443 is busy` | Close the other `app` window (Ctrl+C) and retry |
| `up` stops at a stage | Read the message, fix, re-run `up` (each stage is idempotent) |
| EKS console says it can't show Kubernetes objects | Sign in to the console as `demo-admin`, not root |

The live results recorded so far are in [docs/d2/evidence.md](docs/d2/evidence.md). Detection logic is in [scripts/d2](scripts/d2/README.md) and the infrastructure in [infra](infra/README.md).
