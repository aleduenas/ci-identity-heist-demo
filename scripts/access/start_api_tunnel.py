"""Open the private EKS API through the lab SSM host using operator credentials."""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", required=True, type=Path)
    parser.add_argument("--local-port", type=int, default=8443)
    args = parser.parse_args()
    if not 1024 <= args.local_port <= 65535:
        raise SystemExit("Choose an unprivileged TCP port between 1024 and 65535")
    raw = json.loads(args.outputs.read_text(encoding="utf-8-sig"))
    values = {key: item["value"] for key, item in raw.items()}
    instance = values.get("operations_instance_id")
    if not instance:
        raise SystemExit("Enable the operations host or connect through your own VPC network")
    hostname = values["cluster_endpoint_hostname"]
    parameters = {
        "host": [hostname], "portNumber": ["443"], "localPortNumber": [str(args.local_port)],
    }
    print(f"Keep this session open. API server: https://127.0.0.1:{args.local_port}")
    print(f"TLS server name: {hostname}")
    subprocess.run([
        "aws", "ssm", "start-session", "--region", values["aws_region"],
        "--target", instance, "--document-name", "AWS-StartPortForwardingSessionToRemoteHost",
        "--parameters", json.dumps(parameters),
    ], check=True)


if __name__ == "__main__":
    main()
