"""Apply foundational Kubernetes resources as an explicit bootstrap administrator."""

import argparse
import base64
import json
import os
import subprocess
from pathlib import Path

import yaml
from common import kubeconfig, terraform_outputs
from render import render


def apply(command, resources):
    subprocess.run(
        command + ["apply", "--server-side", "--field-manager=mybank-bootstrap", "-f", "-"],
        input=yaml.safe_dump_all(resources, sort_keys=False),
        text=True,
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()
    api_key = os.environ.get("APP_API_KEY", "")
    if len(api_key) < 32:
        raise SystemExit("APP_API_KEY must be supplied externally with at least 32 characters")
    outputs = terraform_outputs(args.outputs)
    resources = render(args.outputs, args.image)
    namespace = [item for item in resources if item["kind"] == "Namespace"]
    other_resources = [item for item in resources if item["kind"] != "Namespace"]
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "type": "Opaque",
        "metadata": {"name": "mybank-api", "namespace": "mybank"},
        "data": {"api-key": base64.b64encode(api_key.encode()).decode()},
    }
    print(f"Bootstrapping mybank on {outputs['cluster_name']} in {outputs['aws_region']}")
    with kubeconfig(outputs["cluster_name"], outputs["aws_region"]) as command:
        apply(command, namespace)
        # Secret content travels on stdin; it is never written to a file or argv.
        subprocess.run(
            command + ["apply", "--server-side", "--field-manager=mybank-bootstrap", "-f", "-"],
            input=json.dumps(secret),
            text=True,
            check=True,
        )
        apply(command, other_resources)
        subprocess.run(
            command
            + ["-n", "mybank", "rollout", "status", "deployment/mybank-api", "--timeout=300s"],
            check=True,
        )


if __name__ == "__main__":
    main()
