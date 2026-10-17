"""Register/remove the trusted main-only release runner on the private operations host."""

import time

import boto3

from scripts.aws.run import REGION
from scripts.demo.github_api import request
from scripts.demo.ops import ok

LABEL = "mybank-sandbox"


def _ssm():
    return boto3.client("ssm", region_name=REGION)


def _shell(instance: str, commands: list[str], timeout: int = 600) -> tuple[str, str]:
    ssm = _ssm()
    command_id = ssm.send_command(
        InstanceIds=[instance], DocumentName="AWS-RunShellScript",
        Parameters={"commands": commands}, TimeoutSeconds=timeout,
    )["Command"]["CommandId"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(5)
        try:
            result = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if result["Status"] not in ("Pending", "InProgress", "Delayed"):
            return result["Status"], result.get("StandardErrorContent", "")[-800:]
    return "TimedOut", ""


def wait_host_ready(instance: str, timeout: int = 900):
    """SSM Online, then the user-data marker that tools were checksum-verified and installed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = _ssm().describe_instance_information(
            Filters=[{"Key": "InstanceIds", "Values": [instance]}])["InstanceInformationList"]
        if info and info[0]["PingStatus"] == "Online":
            status, _ = _shell(instance, ["test -f /opt/actions-runner/.mybank-ready"], 60)
            if status == "Success":
                ok(f"operations host {instance} online with runner tooling installed")
                return
            failed, _ = _shell(instance, ["cloud-init status | grep -q error"], 60)
            if failed == "Success":
                raise SystemExit("Host user-data failed; inspect /var/log/cloud-init-output.log "
                                 "over SSM (aws ssm start-session --target " + instance + ")")
        time.sleep(15)
    raise SystemExit("Operations host never became ready (check cloud-init on the instance)")


def online_runners(repo: dict) -> list[dict]:
    runners = request("GET", f"{repo['path']}/actions/runners")["runners"]
    return [r for r in runners if LABEL in {label["name"] for label in r["labels"]}]


def register(repo: dict, values: dict):
    if any(r["status"] == "online" for r in online_runners(repo)):
        ok("trusted release runner already online")
        return
    instance, parameter = values["operations_instance_id"], values["runner_parameter_name"]
    token = request("POST", f"{repo['path']}/actions/runners/registration-token")["token"]
    ssm = _ssm()
    ssm.put_parameter(Name=parameter, Value=token, Type="SecureString", Overwrite=True)
    del token
    try:
        status, error = _shell(instance, [
            "set -euo pipefail",
            "cd /opt/actions-runner",
            f"TOKEN=$(aws ssm get-parameter --region {REGION} --name {parameter} "
            "--with-decryption --query Parameter.Value --output text)",
            f"sudo -u runner ./config.sh --unattended --replace --url https://github.com/{repo['full']}"
            f" --token \"$TOKEN\" --name {values['cluster_name']}-ops --labels {LABEL}",
            "unset TOKEN",
            "./svc.sh install runner",
            "./svc.sh start",
        ])
    finally:
        ssm.delete_parameter(Name=parameter)
    if status != "Success":
        raise SystemExit(f"Runner registration failed ({status}): {error}")
    for _ in range(40):
        if any(r["status"] == "online" for r in online_runners(repo)):
            ok("trusted release runner registered and online (label mybank-sandbox)")
            return
        time.sleep(6)
    raise SystemExit("Runner registered but never reported online")


def remove(repo: dict):
    for runner in online_runners(repo):
        request("DELETE", f"{repo['path']}/actions/runners/{runner['id']}")
        ok(f"removed runner registration {runner['name']}")
