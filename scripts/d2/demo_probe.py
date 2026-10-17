"""Harmless PR-editable test entrypoint: obtain exercise identity; touch no EKS/data resources."""

import json
import os
import urllib.parse
import urllib.request
from datetime import UTC, datetime

import boto3
from botocore import UNSIGNED
from botocore.config import Config

MARKER = "b2-repeat-after-main-only-trust"


def main():
    role_arn = os.environ["D2_DEMO_ROLE_ARN"]
    region = os.environ.get("AWS_REGION", "ca-central-1")
    parsed = urllib.parse.urlparse(os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"])
    query = urllib.parse.parse_qsl(parsed.query) + [("audience", "sts.amazonaws.com")]
    url = urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(query)))
    request = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"],
    })
    with urllib.request.urlopen(request, timeout=20) as response:
        token = json.load(response)["value"]
    attempt_time = datetime.now(UTC).isoformat()
    sts = boto3.client("sts", region_name=region, config=Config(signature_version=UNSIGNED))
    assumed = sts.assume_role_with_web_identity(
        RoleArn=role_arn, RoleSessionName=os.environ.get("D2_SESSION_NAME", "release-looking-demo"),
        WebIdentityToken=token, DurationSeconds=900,
    )
    credentials = assumed["Credentials"]
    identity_client = boto3.client(
        "sts", region_name=region, aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials["SessionToken"],
    )
    identity = identity_client.get_caller_identity()
    print(json.dumps({
        "marker": MARKER, "attempt_utc": attempt_time, "account": identity["Account"],
        "assumed_role_arn": identity["Arn"],
        "assumption_request_id": assumed["ResponseMetadata"]["RequestId"],
        "note": "Job output supports execution only; independent D2 collection is authoritative.",
    }))


if __name__ == "__main__":
    main()
