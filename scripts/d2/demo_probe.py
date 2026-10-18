"""Harmless PR-editable test entrypoint: obtain the exercise identity, then show its limits.

It never changes EKS or writes data. After obtaining credentials it only *attempts* what an
attacker would try next, and reports why each attempt fails:
1. read a customer account straight from the database (IAM denies the deploy identity);
2. reach the private EKS API from this GitHub-hosted runner (the network does not route it).
"""

import json
import os
import socket
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError

MARKER = "owned"


def web_identity_token() -> str:
    parsed = urllib.parse.urlparse(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    query = urllib.parse.parse_qsl(parsed.query) + [("audience", "sts.amazonaws.com")]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)["value"]


def try_database(session) -> str:
    table = os.environ.get("D2_ACCOUNTS_TABLE")
    if not table:
        return "skipped (D2_ACCOUNTS_TABLE unset)"
    try:
        session.client("dynamodb").get_item(
            TableName=table, Key={"account_id": {"S": "acct-alice"}})
        return "UNEXPECTED: read succeeded"
    except ClientError as error:
        return f"blocked by IAM: {error.response['Error']['Code']}"


def try_cluster(session) -> str:
    cluster = os.environ.get("EKS_CLUSTER_NAME")
    if not cluster:
        return "skipped (EKS_CLUSTER_NAME unset)"
    endpoint = session.client("eks").describe_cluster(name=cluster)["cluster"]["endpoint"]
    host = urllib.parse.urlparse(endpoint).hostname
    try:
        with socket.create_connection((host, 443), timeout=8):
            return f"UNEXPECTED: reached {host}:443"
    except OSError as error:
        return ("blocked by network: private endpoint unreachable from runner "
                f"({type(error).__name__})")


def main():
    region = os.environ.get("AWS_REGION", "us-east-1")
    attempt_time = datetime.now(UTC).isoformat()
    sts = boto3.client("sts", region_name=region, config=Config(signature_version=UNSIGNED))
    assumed = sts.assume_role_with_web_identity(
        RoleArn=os.environ["D2_DEMO_ROLE_ARN"],
        RoleSessionName=os.environ.get("D2_SESSION_NAME", "release-looking-demo"),
        WebIdentityToken=web_identity_token(), DurationSeconds=900,
    )
    credentials = assumed["Credentials"]
    session = boto3.Session(
        region_name=region, aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    print(json.dumps({
        "marker": MARKER, "attempt_utc": attempt_time,
        "obtained_identity": session.client("sts").get_caller_identity()["Arn"],
        "assumption_request_id": assumed["ResponseMetadata"]["RequestId"],
        "direct_database_read": try_database(session),
        "reach_private_cluster": try_cluster(session),
        "note": "Job output supports execution only; independent D2 collection is authoritative.",
    }, indent=2))


if __name__ == "__main__":
    main()
