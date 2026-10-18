"""Shared demo plumbing: operator AWS session, Terraform, outputs and the private EKS tunnel."""

import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import time
from contextlib import contextmanager

from scripts.aws.run import REGION, ROOT, operator_env

TF = ROOT / ".tools/terraform/terraform.exe"
SANDBOX = ROOT / "infra/environments/sandbox"
CACHE = ROOT / ".cache"
OUTPUTS = CACHE / "outputs.json"
TFVARS = CACHE / "sandbox.tfvars.json"
API_KEY = CACHE / "demo-api-key"


def activate():
    """Make boto3 and every child process use the operator's repository-local login."""
    os.environ.update(operator_env())


def step(message: str):
    print(f"\n==> {message}", flush=True)


def ok(message: str):
    print(f"    [ok] {message}", flush=True)


def exe(name: str) -> str:
    return shutil.which(name, path=os.environ["PATH"]) or name


def run(command: list[str], env: dict | None = None, capture: bool = False) -> str:
    command = [exe(command[0]), *command[1:]]
    result = subprocess.run(command, env=env or os.environ, check=True, text=True,
                            capture_output=capture)
    return result.stdout if capture else ""


def terraform(*args: str, capture: bool = False) -> str:
    return run([str(TF), f"-chdir={SANDBOX}", *args], capture=capture)


def tf_vars(repo: dict, **overrides) -> list[str]:
    """Bind trust to the actual git remote's immutable IDs, so a fresh repository just works."""
    pattern = f"{repo['prefix']}:{{context}}:event_name:{{event_name}}:run_id:*:run_attempt:*"
    values = {"github_owner": repo["owner"], "github_repository": repo["name"],
              "github_oidc_subject_prefix": repo["prefix"], "detection_sub_pattern": pattern,
              **overrides}
    return [f"-var-file={TFVARS}"] + [f"-var={key}={value}" for key, value in values.items()]


def save_outputs() -> dict:
    document = json.loads(terraform("output", "-json", capture=True))
    OUTPUTS.write_text(json.dumps(document, indent=2), encoding="utf-8")
    return outputs()


def outputs() -> dict:
    if not OUTPUTS.exists():
        raise SystemExit("No .cache/outputs.json yet; run `python -m scripts.demo.up` first")
    raw = json.loads(OUTPUTS.read_text(encoding="utf-8-sig"))
    return {key: item["value"] for key, item in raw.items()}


def tfvars() -> dict:
    return json.loads(TFVARS.read_text(encoding="utf-8"))


def api_key() -> str:
    """Lab API key lives only in ignored .cache; created once, reused on re-runs."""
    if not API_KEY.exists():
        API_KEY.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return API_KEY.read_text(encoding="utf-8").strip()


def bootstrap_env() -> dict:
    """Short-lived cluster-admin session from the bootstrap role; never stored on disk."""
    import boto3

    role = tfvars()["bootstrap_admin_role_arns"][0]
    credentials = boto3.client("sts", region_name=REGION).assume_role(
        RoleArn=role, RoleSessionName="mybank-demo-operator", DurationSeconds=3600,
    )["Credentials"]
    env = {**os.environ, "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
           "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"],
           "AWS_SESSION_TOKEN": credentials["SessionToken"]}
    env.pop("AWS_PROFILE", None)
    return env


def _port_open(port: int) -> bool:
    with socket.socket() as probe:
        probe.settimeout(1)
        return probe.connect_ex(("127.0.0.1", port)) == 0


@contextmanager
def eks_tunnel(values: dict, port: int = 8443):
    """SSM port-forward to the private EKS endpoint through the operations host."""
    if _port_open(port):
        raise SystemExit(f"Local port {port} is busy; close the other tunnel first")
    parameters = {"host": [values["cluster_endpoint_hostname"]], "portNumber": ["443"],
                  "localPortNumber": [str(port)]}
    process = subprocess.Popen(
        [exe("aws"), "ssm", "start-session", "--target", values["operations_instance_id"],
         "--document-name", "AWS-StartPortForwardingSessionToRemoteHost",
         "--parameters", json.dumps(parameters)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 90
        while not _port_open(port):
            if process.poll() is not None or time.monotonic() > deadline:
                raise SystemExit("SSM tunnel to the private EKS API did not start")
            time.sleep(1)
        yield {"MYBANK_KUBE_API_SERVER": f"https://127.0.0.1:{port}",
               "MYBANK_KUBE_TLS_SERVER_NAME": values["cluster_endpoint_hostname"]}
    finally:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                           capture_output=True, check=False)
        else:
            process.terminate()
